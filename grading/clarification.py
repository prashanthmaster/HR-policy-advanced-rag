"""
T-4.5: the stateless structured clarification contract (Finding 5).

~25% of the probe set is MUST_CLARIFY, which looks like it collides with
the locked "no chatbot / no conversational memory / stateless
single-turn" scope decision (slot4_design.md). It doesn't: clarification
here is a single terminal response, not a follow-up question that waits
for a reply. The caller re-asks a self-contained question if they want
one answer; nothing is remembered between calls.

Two independent triggers, both surfaced as MissingFact entries:

  1. A temporal fact is missing -- already detected by T-4.3. Every
     TemporalWorking.missing_facts entry (e.g. GRANDFATHERED without a
     joining date, P-06's shape) becomes one MissingFact here. This
     module does not re-derive that signal, only translates it.

  2. The country was never stated, and the retrieved normative clauses
     answer differently in different countries (P-13/P-19/P-41's shape:
     "how much notice do I owe?" with no country given). Detected here:
     if the caller didn't supply a country and the retrieved normative
     pieces span more than one non-GLOBAL country, that's ambiguous --
     silently picking one (e.g. defaulting to India because the corpus
     is India-heavy, P-41's exact trap) is the failure being guarded
     against, not a legitimate shortcut.

For each MissingFact this module CAN branch on (currently: country), it
builds one ConditionalAnswer per plausible value by re-running generation
against the subset of pieces for that value. Facts it can't branch on
(e.g. a missing date, which isn't a small enumerable set) are reported
without conditional_answers -- the missing_facts entry is still Finding
5's contract; not every fact is enumerable.
"""

from __future__ import annotations

from generation.generator import TemplateGenerator
from grading.schema import ClarificationResponse, ConditionalAnswer, MissingFact
from grading.temporal_reasoner import TemporalWorking
from ingestion.logging_setup import get_logger
from retrieval.hybrid_search import RetrievedPiece

_log = get_logger("grading.clarification")

# Why each machine-stable fact name matters -- Finding 5 requires the
# reason to travel with the fact, not just the name.
_FACT_EXPLANATIONS: dict[str, str] = {
    "country": "Retrieved clauses give different answers in different countries; the answer depends on which one applies.",
    "service_start_date": "The applicable version/cohort depends on when continuous service began.",
    "valuation_date": "The applicable version depends on the date the entitlement is being computed as of (termination, payout, or the date being asked about).",
    "cohort_rule": "This clause is grandfathered by cohort but its own cohort test could not be read.",
}


def _why(fact: str) -> str:
    return _FACT_EXPLANATIONS.get(fact, f"'{fact}' is required to compute a determinate answer.")


def detect_missing_facts(
    pieces: list[RetrievedPiece],
    workings: list[TemporalWorking],
    query_country: str | None,
) -> list[MissingFact]:
    missing: list[MissingFact] = []
    seen: set[str] = set()

    countries = {p.unit.country for p in pieces if p.unit.normative and p.unit.country != "GLOBAL"}
    if query_country is None and len(countries) > 1:
        missing.append(MissingFact(fact="country", why=_why("country")))
        seen.add("country")

    for w in workings:
        for fact in w.missing_facts:
            if fact in seen:
                continue
            missing.append(MissingFact(fact=fact, why=_why(fact)))
            seen.add(fact)

    return missing


def build_clarification(
    query: str,
    pieces: list[RetrievedPiece],
    workings: list[TemporalWorking],
    missing_facts: list[MissingFact],
    generator: TemplateGenerator | None = None,
) -> ClarificationResponse:
    """Assumes detect_missing_facts already found something -- callers
    should only reach this when missing_facts is non-empty."""
    generator = generator or TemplateGenerator()
    conditional_answers: list[ConditionalAnswer] = []

    if any(mf.fact == "country" for mf in missing_facts):
        countries = sorted({p.unit.country for p in pieces if p.unit.normative and p.unit.country != "GLOBAL"})
        for country in countries:
            subset = [p for p in pieces if p.unit.country in (country, "GLOBAL")]
            if not subset:
                continue
            answer = generator.generate(query, subset, [])
            conditional_answers.append(ConditionalAnswer(condition=f"if country = {country}", answer=answer))
        _log.info("clarification: branched on country -> %d conditional answers", len(conditional_answers))

    return ClarificationResponse(missing_facts=missing_facts, conditional_answers=conditional_answers)
