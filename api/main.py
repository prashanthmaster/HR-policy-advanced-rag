"""
T-8.4: the real FastAPI backend for Milestone 8.

Deliberately a thin HTTP wrapper over grading.answer_pipeline.answer_query
-- the exact same composed pipeline already unit-tested (Phase 4) and
scored (Phase 5), not a reimplementation. This module's only job is:
build the retriever/reranker/generator once at process startup, expose
them over a POST /query endpoint with a typed request/response contract,
and stay honest about the same scope note answer_query's own docstring
states -- country/jurisdiction_scope/dates are NOT extracted from free
text here; the caller (this API's request body, filled in by the
Streamlit UI) supplies them directly.

Two vector-index modes, chosen automatically at startup from environment
variables -- so the exact same code runs unmodified on Prashanth's laptop
(dev) and on Cloud Run (prod):
  - QDRANT_URL set  -> remote Qdrant Cloud (T-8.2), required in prod because
    Cloud Run containers have no persistent local disk across restarts.
  - QDRANT_URL unset -> local on-disk build/vector_index/ (dev machine only,
    same path scripts/build_vector_index.py --live writes to).

GET /health exists purely for Cloud Run's own startup/liveness checks --
it does not touch the retriever, so it stays fast and cannot fail because
of a slow model load.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

# Defensive strip -- see scripts/build_vector_index.py's docstring for why
# (a secret with a trailing newline/space breaks the Authorization header;
# hit for real in CI, Phase 7 Change Log).
if os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"].strip()

from grading.answer_pipeline import PipelineResult, answer_query  # noqa: E402
from grading.temporal_reasoner import ServiceFacts  # noqa: E402
from ingestion.embedder import EmbeddingCache, OpenAIEmbedder  # noqa: E402
from ingestion.index_units import build_indexable_units  # noqa: E402
from ingestion.logging_setup import get_logger  # noqa: E402
from ingestion.parser import parse_corpus  # noqa: E402
from retrieval.bm25_index import build_bm25_index  # noqa: E402
from retrieval.hybrid_search import HybridRetriever  # noqa: E402
from retrieval.reranker import FlashRankReranker, Reranker  # noqa: E402
from retrieval.vector_index import VectorIndex  # noqa: E402

_log = get_logger("api.main")

app = FastAPI(
    title="HR-Policy Advanced RAG",
    description="Portfolio Slot 4 -- HR-policy RAG with live freshness handling and temporal reasoning.",
    version="1.0.0",
)

# --- populated once at startup by _startup(), read by the /query handler ---
_retriever: HybridRetriever | None = None
_reranker: Reranker | None = None


def _build_retriever() -> HybridRetriever:
    """Same composition as scripts/live_demo.py's _build_retriever, plus
    the Qdrant Cloud branch T-8.2 adds. BM25 always rebuilds from the
    corpus/ directory bundled into the container image -- it is free and
    has no remote counterpart to migrate (see drive_sync/reindex.py's
    docstring, referenced from live_demo.py, for why a fresh BM25 build
    per process start is deliberate, not a shortcut)."""
    corpus_dir = REPO_ROOT / "corpus"
    chunks = parse_corpus(corpus_dir, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)
    bm25 = build_bm25_index(units)

    cache = EmbeddingCache(REPO_ROOT / "build" / "embedding_cache.json")
    embedder = OpenAIEmbedder(cache=cache)

    qdrant_url = os.environ.get("QDRANT_URL")
    if qdrant_url:
        _log.info("api startup: using Qdrant Cloud at %s", qdrant_url)
        vector = VectorIndex(embedder, url=qdrant_url, api_key=os.environ.get("QDRANT_API_KEY"))
    else:
        index_path = REPO_ROOT / "build" / "vector_index"
        _log.info("api startup: using local on-disk Qdrant at %s (dev only)", index_path)
        vector = VectorIndex(embedder, path=index_path)
    vector.open_existing()

    return HybridRetriever(bm25, vector, units)


@app.on_event("startup")
def _startup() -> None:
    global _retriever, _reranker
    if not os.environ.get("OPENAI_API_KEY"):
        # Fail loudly at startup, not on the first request -- a Cloud Run
        # deploy missing the secret should show as a crashed revision, not
        # a 500 on someone's first real query.
        raise RuntimeError("OPENAI_API_KEY is not set -- refusing to start.")

    _retriever = _build_retriever()

    try:
        _reranker = FlashRankReranker()
    except Exception as exc:  # noqa: BLE001
        _log.warning("api startup: proceeding without reranking (%s)", exc)
        _reranker = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The HR-policy question, in plain English.")
    country: str | None = Field(None, description='One of "India", "UAE", "Germany" -- omit to search all.')
    jurisdiction_scope: str | None = Field(None, description="Optional jurisdiction-scope filter.")
    service_start_date: dt.date | None = Field(None, description="Employee's service start date, if the question needs it.")
    valuation_date: dt.date | None = Field(None, description="The 'as of' / termination date the question is anchored to.")
    monthly_wage: float | None = Field(None, description="Last-drawn monthly wage, if a rupee/currency figure is needed.")


class CitationOut(BaseModel):
    clause_id: str
    doc: str
    section: str | None
    version: str | None
    effective_date: dt.date | None


class QueryResponse(BaseModel):
    status: str  # "ANSWERED" | "NEEDS_CLARIFICATION" | "INSUFFICIENT"
    answer_text: str | None = None
    citations: list[CitationOut] = []
    computed_amount: float | None = None
    computed_days: float | None = None
    superseded_warning: str | None = None
    missing_facts: list[dict] = []
    conditional_answers: list[dict] = []
    insufficient_reasons: list[str] = []


def _to_response(result: PipelineResult) -> QueryResponse:
    if result.status == "ANSWERED":
        a = result.answer
        return QueryResponse(
            status=result.status,
            answer_text=a.text,
            citations=[
                CitationOut(clause_id=c.clause_id, doc=c.doc, section=c.section, version=c.version, effective_date=c.effective_date)
                for c in a.citations
            ],
            computed_amount=a.computed_amount,
            computed_days=a.computed_days,
            superseded_warning=a.superseded_warning,
        )
    if result.status == "NEEDS_CLARIFICATION":
        c = result.clarification
        return QueryResponse(
            status=result.status,
            missing_facts=[{"fact": m.fact, "why": m.why} for m in c.missing_facts],
            conditional_answers=[{"condition": ca.condition} for ca in c.conditional_answers],
        )
    # INSUFFICIENT
    return QueryResponse(
        status=result.status,
        insufficient_reasons=[r.value for r in result.sufficiency.reasons] if result.sufficiency else [],
    )


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    if _retriever is None:
        raise HTTPException(status_code=503, detail="Retriever not ready yet -- try again shortly.")

    facts = ServiceFacts(
        service_start_date=req.service_start_date,
        valuation_date=req.valuation_date,
        monthly_wage=req.monthly_wage,
    )
    try:
        result = answer_query(
            _retriever,
            req.query,
            country=req.country,
            jurisdiction_scope=req.jurisdiction_scope,
            as_of_date=req.valuation_date,
            facts=facts,
            reranker=_reranker,
        )
    except Exception as exc:  # noqa: BLE001
        _log.exception("query failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _to_response(result)
