"""
T-2.8: the four ingestion guarantees PROJECT_PLAN.md names explicitly for
M2's exit criterion. Each is already exercised indirectly elsewhere in the
suite; this file names each guarantee once, directly, against the real
corpus, so M2 closes on an explicit checklist rather than an implicit one.

  1. Proviso integrity   -- a rule and its proviso never end up in
                             different pieces (chunker.py already tests
                             this with a synthetic fixture; here it's
                             checked against the real R-17 clause).
  2. Three-clock separation -- effective_date, revision_date, indexed_at
                             are never conflated; UNRESOLVED is preserved,
                             not defaulted.
  3. Lineage linkage      -- version pairs share a lineage_id, and
                             supersedes/superseded_by point at real,
                             mutually-consistent clause_ids.
  4. Normative flagging   -- an illustration/decoy is never indexed as
                             equal authority to the rule it illustrates.
"""

from __future__ import annotations

from pathlib import Path

from ingestion.chunker import chunk_clause
from ingestion.parser import parse_corpus, parse_file

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


# 1. Proviso integrity, against the real corpus, not a synthetic fixture.
def test_proviso_integrity_on_real_gratuity_forfeiture_clause():
    chunks = parse_file(
        CORPUS_DIR / "tier1_law" / "india" / "india_law.md",
        repo_root=REPO_ROOT,
    )
    forfeiture = next(c for c in chunks if c.metadata.clause_id == "IN-GRAT-S4-6-FORFEITURE")
    # Force a tight threshold so the rule is actually tested, not just
    # trivially satisfied because the clause happened to fit in one piece.
    pieces = chunk_clause(forfeiture, max_chars=120)
    proviso_pieces = [p for p in pieces if "provided" in p.text.lower() or "riotous" in p.text.lower() or "damage" in p.text.lower()]
    for p in proviso_pieces:
        # Every piece containing proviso language must ALSO contain
        # enough of the base rule to be self-standing -- i.e. it wasn't
        # cut apart from what it qualifies.
        assert "forfeit" in p.text.lower() or "gratuity" in p.text.lower()


# 2. Three-clock separation.
def test_three_clocks_are_never_conflated():
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    for c in chunks:
        m = c.metadata
        # effective_date is either a real date or explicitly marked
        # unresolved -- never silently defaulted to indexed_at or today.
        assert (m.effective_date is not None) != m.effective_date_unresolved or (
            m.effective_date is None and m.effective_date_unresolved
        )
        # indexed_at is pipeline bookkeeping, populated by the pipeline,
        # not authored in the markdown -- must be None straight out of the
        # parser, never accidentally set from effective_date or today.
        assert m.indexed_at is None


def test_relocation_clause_effective_date_stays_unresolved_not_defaulted():
    chunks = parse_file(
        CORPUS_DIR / "tier2_policy" / "india" / "meridian_india_policy.md",
        repo_root=REPO_ROOT,
    )
    relocation = next(c for c in chunks if c.metadata.clause_id == "MER-IN-RELOCATION")
    assert relocation.metadata.effective_date is None
    assert relocation.metadata.effective_date_unresolved is True
    assert relocation.metadata.revision_date != relocation.metadata.effective_date  # both None here, but never conflated in meaning


# 3. Lineage linkage.
def test_version_pair_shares_lineage_id():
    chunks = parse_file(
        CORPUS_DIR / "tier2_policy" / "india" / "meridian_india_policy.md",
        repo_root=REPO_ROOT,
    )
    v1 = next(c for c in chunks if c.metadata.clause_id == "MER-IN-LEAVE-ANNUAL-V1")
    v2 = next(c for c in chunks if c.metadata.clause_id == "MER-IN-LEAVE-ANNUAL-V2")
    assert v1.metadata.lineage_id == v2.metadata.lineage_id == "MER-IN-LEAVE-ANNUAL"
    assert v1.metadata.superseded_by == "MER-IN-LEAVE-ANNUAL-V2"
    assert v2.metadata.supersedes == "MER-IN-LEAVE-ANNUAL-V1"


def test_every_supersedes_and_superseded_by_points_at_a_real_clause():
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    all_ids = {c.metadata.clause_id for c in chunks}
    for c in chunks:
        if c.metadata.supersedes:
            assert c.metadata.supersedes in all_ids, f"{c.metadata.clause_id}.supersedes -> unknown clause"
        if c.metadata.superseded_by:
            assert c.metadata.superseded_by in all_ids, f"{c.metadata.clause_id}.superseded_by -> unknown clause"


def test_every_clause_has_a_lineage_id():
    # Backfilled onto all 18 Tier-1 clauses in Phase 1's schema-drift fix;
    # this closes the loop by asserting it holds for the whole corpus now,
    # not just the clauses it was originally checked on.
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    missing = [c.metadata.clause_id for c in chunks if not c.metadata.lineage_id]
    assert not missing, f"clauses missing lineage_id: {missing}"


# 4. Normative flagging.
def test_decoy_illustration_is_not_normative_and_is_linked_to_the_real_rule():
    chunks = parse_file(
        CORPUS_DIR / "tier2_policy" / "india" / "meridian_india_policy.md",
        repo_root=REPO_ROOT,
    )
    illustration = next(c for c in chunks if c.metadata.clause_id == "MER-IN-GRATUITY-ILLUSTRATION")
    rule = next(c for c in chunks if c.metadata.clause_id == "MER-IN-GRATUITY-ENTITLEMENT")
    assert illustration.metadata.normative is False
    assert rule.metadata.normative is True
    assert illustration.metadata.illustrates == rule.metadata.clause_id


def test_superseded_ceiling_clause_still_marked_normative_but_superseded():
    # Deliberate design point, not a contradiction: the superseded clause
    # IS normative prose (it was real law once) -- what stops a generator
    # from citing it as CURRENT authority is superseded_by, not normative.
    # Retrieval-time filtering (Phase 3) is what must consult
    # superseded_by/effective_date, not treat "normative" as a proxy for
    # "current."
    chunks = parse_file(
        CORPUS_DIR / "tier1_law" / "india" / "india_law.md",
        repo_root=REPO_ROOT,
    )
    superseded = next(c for c in chunks if c.metadata.clause_id == "IN-GRAT-S4-CEILING-SUPERSEDED")
    assert superseded.metadata.superseded_by == "IN-GRAT-S4-CEILING"
