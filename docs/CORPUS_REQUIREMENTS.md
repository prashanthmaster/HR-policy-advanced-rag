# Corpus Requirements Spec (reverse-engineered)

This spec is **output**, not input. It is what falls out of `docs/FAILURE_MODES.md` and `eval/golden/adversarial_probe_set.md` once the probes are written first. Every requirement below exists because a specific probe needs something to bite on; nothing is here because it seemed like a realistic thing for an HR manual to contain.

The fictional company is **Meridian Global Services** — a labelled synthetic entity. Every Tier-2 file carries a synthetic-content banner. Tier-1 (real statutory law) is already built and is not modified by any requirement here.

---

## Part 1 — Chunk schema (extends the Tier-1 metadata block)

Tier-1 chunks already carry: `clause_id`, `country`, `doc_type`, `section`, `effective_date`, `version`, `source_url`. The adversarial pass adds five fields, each traceable to a finding:

| Field | Values | Why (finding / FM) |
|---|---|---|
| `temporal_applicability` | `POINT_IN_TIME` · `SEGMENTED_ACCRUAL` · `GRANDFATHERED` · `ELECTIVE` | Finding 1. Not inferable at retrieval time; the straddle case is unanswerable without it. |
| `revision_date` | date | Finding 2. Drive `modifiedTime`. **Distinct from `effective_date`.** Never used for as-of filtering. |
| `indexed_at` | timestamp | Finding 2. Pipeline bookkeeping. Third clock. |
| `normative` | `true` · `false` | FM-D5. Worked examples and illustrations are `false` and may never be cited as authority. |
| `lineage_id` | stable id across versions | FM-A5, A6, A8, D6, E6. Supersession and dedup work on lineage, not on filename or clause number. |

Plus, where applicable: `supersedes` / `superseded_by` (clause-level, per FM-A6), `cohort_rule` (for `GRANDFATHERED`), `jurisdiction_scope` (mainland / free-zone / state).

**Ingestion must also classify each detected change** as `NO_OP` · `EDITORIAL` · `SUBSTANTIVE` · `ADDITION` · `SUNSET` (Finding 4). Only `SUBSTANTIVE` and `SUNSET` create version events — otherwise a typo fix fires a false amendment alert and the freshness demo becomes noise.

---

## Part 2 — Required corpus features

Each row is a thing that must be **deliberately constructed**. The probe column is the reason it exists.

### Versioning structures

| # | Required feature | Probes | Notes |
|---|---|---|---|
| R-01 | **Version pair, `SEGMENTED_ACCRUAL`** — leave accrual 18 → 24 days/yr, amended mid-timeline | P-02 | The correct-to-split counterpart to India's ceiling. Both must be in the corpus or neither probe proves anything. |
| R-02 | **Grandfathered amendment** — applies only to joiners on/after 2025-01-01; both versions simultaneously current | P-06 | Needs `cohort_rule`. |
| R-03 | **Future-dated amendment** — published now, effective next year | P-05 | The probe most likely to expose a naive "newest wins" retriever. |
| R-04 | **Retroactive amendment** — `revision_date` after `effective_date` | P-04 | Forces the three-clock separation to be real, not decorative. |
| R-05 | **Silent supersession** — superseded version left in the Drive folder, no marker in the text | P-07 | Lineage must carry it. |
| R-06 | **Partial supersession** — one clause amended in an otherwise unchanged document | P-08 | Kills doc-level versioning. |
| R-07 | **Expired policy, no successor** — temporary WFH allowance, sunset date passed | P-09 | Absence is the answer. |
| R-08 | **Clause renumbering** — "7.2" means different things in v1 and v2 | P-10 | Never match on number alone. |
| R-09 | **Vague effective date** — a clause saying "with immediate effect" | P-11 | Ambiguity must survive ingestion rather than being resolved away. |

### Conflict structures

| # | Required feature | Probes | Notes |
|---|---|---|---|
| R-10 | **Policy above the statutory floor** — 45 days notice where statute floors at 30 | P-15 | Policy governs. |
| R-11 | **Policy below the statutory floor** — 15 days notice for a grade where statute floors at 30 | P-16 | **Deliberately unenforceable.** Must carry an in-file comment saying it is intentionally non-compliant so a reader never mistakes it for drafting sloppiness. Resolution is asymmetric with R-10 — that asymmetry is the point. |
| R-12 | **Free-zone annexe** — DIFC/ADGM chapter diverging from UAE mainland | P-17 | `jurisdiction_scope`. `[VERIFY]` before golden answers. |
| R-13 | **Near-identical cross-country clauses** — same wording, different numbers, India vs UAE | P-18, P-20 | Forces hard metadata filtering over soft embedding preference. |
| R-14 | **Divergent definitions** — "wages" base and "probation" defined differently per country | P-19, P-20, P-32 | |
| R-15 | **Governing-law clause** — how the company determines applicable jurisdiction for a cross-border employee | P-14 | Must be genuinely incomplete on the nationality-vs-location-vs-payroll triangle, so the correct behaviour is to clarify rather than guess. |

### Retrieval-mechanic structures

| # | Required feature | Probes | Notes |
|---|---|---|---|
| R-16 | **Two-dimensional slab table** — allowance by grade × tenure | P-30 | Serialised row-wise as text in a separate chunk stream (per the locked no-vision decision). The concrete justification for the hybrid retriever. |
| R-17 | **Clause with a material proviso** — gratuity forfeiture on termination for misconduct | P-31 | Chunker must never separate proviso from clause. Highest-value D-family probe: the failure is grounded-but-wrong, invisible to Faithfulness. |
| R-18 | **Cross-referencing definition** — clause says "as defined in Section 2(s)", definition elsewhere | P-32 | |
| R-19 | **Synonym spread** — EOSB / end-of-service / gratuity / severance / final settlement across chapters | P-33 | |
| R-20 | **Worked example beside its clause**, using ₹50,000 — a figure a probe asks about directly | P-34 | `normative: false`. The decoy must be *more* lexically attractive than the clause it illustrates, or it isn't testing anything. |
| R-21 | **Minimally-differing version pair** (~95% identical) | P-35 | Forces lineage dedup before rerank. |
| R-22 | **Scattered operands** — UAE settlement needs rate bands + wage base + 2-year cap in three separate clauses | P-36 | Partial retrieval must refuse, not part-compute. |
| R-23 | **An oddly-worded rare clause** — low lexical and semantic salience | FM-D8 | Honest known-weakness probe. |
| R-24 | **False-premise bait** — probation stated as 6 months, so "our 60-day probation policy" is checkably false | P-23 | |
| R-25 | **Gap: no paternity leave clause anywhere** | P-39 | A deliberate absence. Must be documented as intentional so a later contributor doesn't "helpfully" fill it in and silently destroy the probe. |

---

## Part 3 — Build order

1. **R-11, R-20, R-25 first.** Each is a thing that looks like a mistake — a non-compliant clause, a decoy, a hole. Writing them first, with their intent recorded, prevents anyone (including a later session of me) from tidying them away.
2. Version-pair structures (R-01 → R-09) — the differentiator's test surface.
3. Conflict structures (R-10 → R-15).
4. Retrieval-mechanic structures (R-16 → R-24).
5. Only then fill in ordinary connective policy prose, so the corpus reads like a real manual rather than a test fixture.

Ordinary prose is written **last and deliberately**, because a manual that is nothing but edge cases is not a realistic retrieval environment — the distractor mass is part of the test.

---

## Part 4 — Standing constraints

- Every Tier-2 file carries a synthetic-content banner naming Meridian Global Services as fictional. Non-negotiable, per the locked corpus design.
- No Tier-2 clause may contradict a Tier-1 statutory clause **except** R-11, which is deliberately non-compliant and labelled as such in-file.
- Deliberate defects (R-11, R-20, R-23, R-25) are listed in a `docs/DELIBERATE_DEFECTS.md` manifest. Anything that looks like a bug and is actually a fixture gets recorded there, or it will eventually be "fixed".
- No probe becomes a scored golden item while it carries `[VERIFY]`. P-01 (ceiling commencement) and P-17 (DIFC divergence) closed 2026-09-03 (V-1, V-3) and are unblocked. The UAE 1980→2021 transition case (V-2) remains open, but was never built as a corpus fixture or tied to any of the 43 probes — DIFC/DEWS (V-3) took the real-straddle-case role instead — so it does not block any current promotion; it stays open as future corpus work.
