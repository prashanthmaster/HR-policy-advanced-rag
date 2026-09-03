"""
T-3.2/T-3.3/T-3.4: hard metadata filters, as-of-date lineage resolution,
and lineage dedup, applied to retrieval candidates.

All three operate on ingestion.index_units.IndexableUnit -- the same flat
per-piece metadata BM25 and vector indexing already carry -- so retrieval
never has to re-look-up a clause_id's metadata mid-query.

Design note shared by T-3.2 and T-3.3: everything here is a HARD filter
(pass/fail), never a score adjustment. FM-B6 is explicit that
cross-country contamination ("gratuity" embeds near-identically across
India and UAE) must be closed by a metadata filter, not a soft embedding
preference the retriever could still override on a strong semantic match.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from ingestion.index_units import IndexableUnit


# ---------------------------------------------------------------------
# T-3.2 -- hard filters: country, jurisdiction_scope
# ---------------------------------------------------------------------


def filter_by_country(units: list[IndexableUnit], country: str | None) -> list[IndexableUnit]:
    """Keep units whose country matches exactly, plus GLOBAL units (the
    Meridian preamble -- scope, governing-law silence, amendment
    procedure -- applies across all three jurisdictions at once, per
    ingestion/schema.py's country validator). country=None means no
    country was determined for this query (e.g. P-13/P-19-style
    no-country probes) -- returns units unchanged, since narrowing on an
    unknown country would be the silent-pick failure those probes test
    for, not a legitimate filter."""
    if country is None:
        return units
    return [u for u in units if u.country == country or u.country == "GLOBAL"]


def filter_by_jurisdiction_scope(
    units: list[IndexableUnit], jurisdiction_scope: str | None
) -> list[IndexableUnit]:
    """Keep units whose jurisdiction_scope matches exactly, plus units
    that carry no jurisdiction_scope at all (None -- e.g. India/Germany
    clauses, which don't subdivide the way UAE mainland/DIFC do, and the
    GLOBAL preamble). jurisdiction_scope=None means the caller did not
    resolve a sub-jurisdiction (e.g. UAE mainland vs DIFC, per FM-B5 /
    P-17) -- returns units unchanged rather than guessing one."""
    if jurisdiction_scope is None:
        return units
    return [u for u in units if u.jurisdiction_scope in (None, jurisdiction_scope)]


def apply_hard_filters(
    units: list[IndexableUnit],
    country: str | None = None,
    jurisdiction_scope: str | None = None,
) -> list[IndexableUnit]:
    return filter_by_jurisdiction_scope(filter_by_country(units, country), jurisdiction_scope)


# ---------------------------------------------------------------------
# T-3.3 -- as-of-date filter on effective_date (Finding 2: never revision_date)
# ---------------------------------------------------------------------


def select_current_as_of(
    units: list[IndexableUnit], as_of_date: dt.date
) -> list[IndexableUnit]:
    """Within each lineage_id group, keep only the version whose
    effective_date is the latest one <= as_of_date -- i.e. the version
    actually in force on that date. Units with no lineage_id (no version
    history to resolve) pass through unchanged. Units with
    effective_date_unresolved=True (the deliberate R-09 gap) also pass
    through unchanged -- the pipeline must preserve that silence, not
    default it to "current" or drop it.

    This closes both directions of Finding 2 on its own: a future-dated
    amendment (effective_date > as_of_date) is excluded, so "newest
    document" can never win by accident (P-05); a retroactive amendment
    (effective_date <= as_of_date even though revision_date is later) is
    included, because filtering is on effective_date, never revision_date
    (P-04).

    Scope note: this resolves WHICH VERSION governs as of a date. It does
    NOT implement the four temporal_applicability regimes themselves
    (POINT_IN_TIME / SEGMENTED_ACCRUAL / GRANDFATHERED / ELECTIVE) --
    that reasoning, over a case whose relevant period straddles a
    boundary, is T-4.3's job once a clause's applicability class is known.
    Retrieval's job here is narrower: don't hand the generator two
    competing "current" versions of the same rule.
    """
    by_lineage: dict[str, list[IndexableUnit]] = defaultdict(list)
    unversioned: list[IndexableUnit] = []
    for u in units:
        if u.lineage_id is None or u.effective_date_unresolved:
            unversioned.append(u)
        else:
            by_lineage[u.lineage_id].append(u)

    kept: list[IndexableUnit] = list(unversioned)
    for _, versions in by_lineage.items():
        eligible = [v for v in versions if v.effective_date is not None and v.effective_date <= as_of_date]
        if not eligible:
            # every version of this lineage is future-dated relative to
            # as_of_date -- nothing in this lineage was in force yet, so
            # nothing from it is retrievable as current.
            continue
        current = max(eligible, key=lambda v: v.effective_date)
        kept.append(current)
    return kept


# ---------------------------------------------------------------------
# T-3.4 -- lineage dedup + diversity before rerank (FM-D6)
# ---------------------------------------------------------------------


def dedup_by_lineage(ranked_piece_ids: list[str], units_by_piece_id: dict[str, IndexableUnit]) -> list[str]:
    """FM-D6: near-duplicate versions of the same clause (v1/v2, ~95%
    identical text) can both land in top-k and squeeze out the actual
    answer. Given a ranked (best-first) list of piece_ids, keep only the
    first (highest-ranked) occurrence of each lineage_id; pieces with no
    lineage_id are never deduplicated against each other.

    This is a safety net independent of select_current_as_of: it applies
    to whatever the fused ranking actually contains, so it still protects
    top-k even when a caller runs without an as-of filter (e.g. a
    version-agnostic query) or when two DIFFERENT lineages happen to
    describe near-duplicate text.
    """
    seen_lineages: set[str] = set()
    out: list[str] = []
    for pid in ranked_piece_ids:
        unit = units_by_piece_id.get(pid)
        lineage = unit.lineage_id if unit else None
        if lineage is not None:
            if lineage in seen_lineages:
                continue
            seen_lineages.add(lineage)
        out.append(pid)
    return out
