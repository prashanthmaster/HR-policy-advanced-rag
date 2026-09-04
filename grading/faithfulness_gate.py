"""
T-6.6 -- faithfulness reused live as a refusal gate.

Phase 5 measured RAGAS Faithfulness after the fact, over a batch, purely
as a quality metric. This module reuses that SAME real metric live, per
answer: once answer_query() reaches ANSWERED, this checks the generated
answer's faithfulness against the actual retrieved context it cited, and
if the score comes back below a threshold, converts the result into a
refusal (INSUFFICIENT) instead of returning a possibly-unsupported answer.

The interview question this exists to answer: "Your guardrail is a
faithfulness score. What stops it refusing everything?" -- and the honest
answer requires that DEFAULT_FAITHFULNESS_THRESHOLD is NOT picked here.
Same discipline as Session 6's min_rerank_score (see
slot4_plan_and_conventions.md Convention 14): an unmeasured constant is
never invented -- it is calibrated from a real run over the scored golden
set (scripts/calibrate_faithfulness_gate.py), checked specifically against
the over-refusal counter (Risk RK-2), not in isolation. The threshold
stays None (gate is a no-op pass-through) until that real number exists.

Deliberately NOT wired into answer_query() itself, to avoid a circular
import (this module needs PipelineResult) and because gating is a policy
decision a caller should make explicitly, not something baked silently
into the retrieval/generation pipeline -- a caller (the API layer,
scripts/reindex_from_drive.py's future demo query, an eval script) calls
apply_faithfulness_gate() itself, after answer_query() returns.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from grading.answer_pipeline import PipelineResult
from ingestion.logging_setup import get_logger

_log = get_logger("grading.faithfulness_gate")

# Calibrated 4 Sep 2026 (Session 10) from a real run of
# scripts/calibrate_faithfulness_gate.py over 13 ANSWERED golden items.
# Real finding: even currently-correct answers scored faithfulness in the
# 0.333-0.737 range (never near 1.0) -- consistent with Phase 5's own
# measured baseline (mean 0.497, Session 8) -- because this pipeline's
# generator is deterministic and citation-grounded (real clause text +
# computed figures) rather than free-form LLM prose, and RAGAS's
# Faithfulness metric decomposes an answer into claims and checks each
# against literal retrieved text; a correct *reasoning* sentence about
# which clause version governs isn't always a literal quote from any one
# clause. At the real measured data: threshold 0.30 refuses ZERO of the
# 13 real ANSWERED items (no regression risk), while 0.40+ already wrongly
# refuses 2+ of them and 0.50+ refuses the majority -- exactly the
# refuse-everything failure mode Risk RK-2 warns against. 0.30 is
# therefore a real trip-wire against a genuinely degenerate future answer
# (nothing today scores anywhere near that low), not a claim that 0.30 is
# a "good enough" faithfulness bar in the abstract. See PROJECT_PLAN.md
# Phase 6 Change Log for the full real numbers and reasoning; per-item
# scores are in build/faithfulness_calibration_result.json.
DEFAULT_FAITHFULNESS_THRESHOLD: float | None = 0.30


class FaithfulnessScorer(Protocol):
    def __call__(self, question: str, answer: str, contexts: list[str]) -> float: ...


def apply_faithfulness_gate(
    result: PipelineResult,
    query: str,
    scorer: FaithfulnessScorer,
    threshold: float | None,
) -> PipelineResult:
    """Returns `result` unchanged unless result.status == "ANSWERED",
    threshold is not None, and this specific answer's live faithfulness
    score comes back below threshold -- in which case a NEW PipelineResult
    with status="INSUFFICIENT" is returned (a live refusal), carrying the
    score for transparency. Never mutates `result` in place.

    `scorer` is injected (not hardcoded to grading.ragas_client.
    score_faithfulness) specifically so tests can pass a fake, deterministic
    scorer and never make a real OpenAI call."""
    if threshold is None or result.status != "ANSWERED" or result.answer is None:
        return result

    contexts = [p.text for p in (result.pieces or [])]
    score = scorer(query, result.answer.text, contexts)
    _log.info("faithfulness gate: score=%.3f threshold=%.3f", score, threshold)

    if score < threshold:
        _log.info("faithfulness gate: REFUSING (score %.3f below threshold %.3f)", score, threshold)
        return replace(
            result,
            status="INSUFFICIENT",
            faithfulness_score=score,
            refused_by_faithfulness_gate=True,
        )

    return replace(result, faithfulness_score=score)
