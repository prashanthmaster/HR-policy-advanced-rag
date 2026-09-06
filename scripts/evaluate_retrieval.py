"""Run the frozen Phase 4 retrieval exam with real OpenAI dense and BM25 sparse vectors."""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import os
import subprocess
from collections import defaultdict
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient

from hr_policy_rag.corpus import load_verified_corpus
from hr_policy_rag.domain import CaseFacts, PolicyTopic
from hr_policy_rag.evaluation import (
    RetrievalAggregate,
    RetrievalCaseScore,
    RetrievalEvaluationMode,
    RetrievalEvaluationReport,
    RetrievalSplit,
    aggregate_scores,
    canonical_text_sha256,
    load_retrieval_case_set,
    passes_thresholds,
    score_case,
)
from hr_policy_rag.ingestion import build_ingestion_bundle
from hr_policy_rag.retrieval import (
    EmbeddingAuthenticationError,
    FastEmbedBm25Encoder,
    OpenAIDenseEncoder,
    QdrantHybridRetriever,
    RetrievalUnavailableError,
    build_candidate_index,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS_MANIFEST = ROOT / "corpus_v2" / "manifest.json"
CASE_SET = ROOT / "evaluation" / "v2" / "retrieval_cases.json"
LOCKFILE = ROOT / "uv.lock"


class EvaluationConfigurationError(RuntimeError):
    """Local evaluation configuration is missing or contradictory."""


def _load_openai_key() -> None:
    env_path = ROOT / ".env"
    file_key = dotenv_values(env_path).get("OPENAI_API_KEY") if env_path.exists() else None
    process_key = os.getenv("OPENAI_API_KEY")
    if file_key and process_key and file_key != process_key:
        raise EvaluationConfigurationError(
            "OPENAI_API_KEY differs between the process and .env; remove the stale process variable"
        )
    load_dotenv(env_path, override=False)
    if not os.getenv("OPENAI_API_KEY"):
        raise EvaluationConfigurationError("OPENAI_API_KEY is missing from the local .env or process environment")


def _git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


async def _run(*, release: bool, output: Path) -> bool:
    if output.exists():
        raise FileExistsError(f"evaluation output is immutable and already exists: {output}")
    _load_openai_key()

    corpus = load_verified_corpus(CORPUS_MANIFEST, repository_root=ROOT)
    bundle = build_ingestion_bundle(corpus, repository_root=ROOT)
    case_set = load_retrieval_case_set(CASE_SET)
    if case_set.corpus_generation != bundle.manifest.corpus_generation:
        raise EvaluationConfigurationError("retrieval exam and ingestion artifact use different corpus generations")

    included_splits = set(RetrievalSplit) if release else {RetrievalSplit.DEVELOPMENT, RetrievalSplit.REGRESSION}
    cases = [case for case in case_set.cases if case.split in included_splits]
    dense = OpenAIDenseEncoder(AsyncOpenAI(timeout=30, max_retries=2))
    sparse = FastEmbedBm25Encoder()
    client = AsyncQdrantClient(":memory:")
    created_at = dt.datetime.now(dt.UTC)
    collection = f"phase4_{created_at:%Y%m%d_%H%M%S_%f}"
    try:
        index_manifest = await build_candidate_index(
            client=client,
            collection_name=collection,
            artifact=bundle.manifest,
            chunks=bundle.chunks,
            dense_encoder=dense,
            sparse_encoder=sparse,
            created_at=created_at,
            create_payload_indexes=False,
        )
        retriever = QdrantHybridRetriever(
            client=client,
            collection_name=collection,
            dense_encoder=dense,
            sparse_encoder=sparse,
        )
        sources = {source.source_id: source for source in corpus.manifest.sources}
        scores: list[RetrievalCaseScore] = []
        for case in cases:
            try:
                evidence = await retriever.retrieve(
                    query=case.query,
                    facts=CaseFacts(
                        country=case.jurisdiction,
                        topic=PolicyTopic(case.topic),
                        as_of_date=case.as_of_date,
                    ),
                    corpus_generation=case_set.corpus_generation,
                    limit=10,
                )
                scores.append(score_case(case, evidence, sources))
            except Exception as exc:
                scores.append(score_case(case, (), sources, error_code=type(exc).__name__))

        aggregate = aggregate_scores(scores)
        scores_by_id = {score.case_id: score for score in scores}
        slices: dict[str, RetrievalAggregate] = {}
        grouped: defaultdict[tuple[str, str], list[RetrievalCaseScore]] = defaultdict(list)
        for case in cases:
            grouped[(case.jurisdiction, case.topic)].append(scores_by_id[case.case_id])
        slice_aggregates: list[RetrievalAggregate] = []
        for (jurisdiction, topic), values in sorted(grouped.items()):
            slice_aggregate = aggregate_scores(values)
            slice_aggregates.append(slice_aggregate)
            slices[f"{jurisdiction}:{topic}"] = slice_aggregate
        passed = passes_thresholds(aggregate, case_set.thresholds, slice_aggregates)
        report = RetrievalEvaluationReport(
            schema_version=1,
            mode=RetrievalEvaluationMode.RELEASE if release else RetrievalEvaluationMode.DEVELOPMENT,
            created_at=created_at,
            git_sha=_git_sha(),
            lockfile_sha256=canonical_text_sha256(LOCKFILE),
            case_set_sha256=case_set.cases_sha256,
            included_splits=tuple(sorted(included_splits, key=lambda item: item.value)),
            index_manifest=index_manifest,
            embedding_tokens=dense.total_tokens,
            thresholds=case_set.thresholds,
            aggregate=aggregate,
            slices=slices,
            passed=passed,
            cases=tuple(scores),
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return passed
    finally:
        await client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--development", action="store_true", help="run development and regression cases only")
    mode.add_argument("--release", action="store_true", help="run the frozen holdout in addition to visible cases")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        passed = asyncio.run(_run(release=args.release, output=args.output))
    except (EvaluationConfigurationError, FileExistsError) as exc:
        parser.error(str(exc))
    except EmbeddingAuthenticationError:
        parser.exit(2, "EMBEDDING_AUTH_FAILED: OpenAI rejected the configured API key\n")
    except RetrievalUnavailableError as exc:
        cause = exc.__cause__
        detail = f"; cause={type(cause).__name__}: {cause}" if cause is not None else ""
        parser.exit(2, f"RETRIEVAL_UNAVAILABLE: {exc}{detail}\n")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
