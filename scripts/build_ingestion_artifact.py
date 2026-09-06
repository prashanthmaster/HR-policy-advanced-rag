"""Build or verify deterministic Phase 3 ingestion artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from hr_policy_rag.corpus import load_verified_corpus
from hr_policy_rag.ingestion import build_ingestion_bundle, render_chunks_jsonl, render_ingestion_manifest

ROOT = Path(__file__).resolve().parents[1]
CORPUS_MANIFEST_PATH = ROOT / "corpus_v2" / "manifest.json"
ARTIFACT_DIR = ROOT / "artifacts" / "v2" / "ingestion"
CHUNKS_PATH = ARTIFACT_DIR / "chunks.jsonl"
INGESTION_MANIFEST_PATH = ARTIFACT_DIR / "manifest.json"


def _matches(path: Path, expected: str) -> bool:
    try:
        return path.read_text(encoding="utf-8") == expected
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    corpus = load_verified_corpus(CORPUS_MANIFEST_PATH, repository_root=ROOT)
    bundle = build_ingestion_bundle(corpus, repository_root=ROOT)
    chunks_jsonl = render_chunks_jsonl(bundle.chunks)
    manifest_json = render_ingestion_manifest(bundle.manifest)

    if args.check:
        chunks_match = _matches(CHUNKS_PATH, chunks_jsonl)
        manifest_matches = _matches(INGESTION_MANIFEST_PATH, manifest_json)
        return 0 if chunks_match and manifest_matches else 1

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    CHUNKS_PATH.write_text(chunks_jsonl, encoding="utf-8")
    INGESTION_MANIFEST_PATH.write_text(manifest_json, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
