# Prompt to paste into the Phase 3 chat

We need to reopen Phase 3 (`retrieval/hybrid_search.py`, already marked `DONE`
in PROJECT_PLAN.md) to fix a real bug found downstream in Phase 5 evaluation,
traced all the way back to retrieval.

## The bug, as discovered

Running the T-5.4 Citation Accuracy eval for real (24-item golden set, live
gpt-4o-mini judge) showed 7/7 ANSWERED items citing 9-12 clauses each when
the golden set expected 1-3. Example: query "Grade M3, 6 years, Dubai --
what's my housing allowance?" (expects only `MER-AE-HOUSING-TABLE`) produced
an answer narrating ~10 unrelated clauses — DIFC leave, notice periods,
probation, EOSB, gratuity ceilings — none of which have anything to do with
housing allowance.

Traced the root cause through three layers:
1. `generation/generator.py`'s `TemplateGenerator.generate()` builds
   citations from every piece in the retrieved-and-graded set, not just
   what the answer's narrative used. (Already patched this specific
   symptom in commit `48daa40` -- narrowed citations to
   `TemporalWorking.governing_piece`/`segments`/`alternatives`. Kept, but
   turned out to be necessary and NOT sufficient.)
2. `grading/temporal_reasoner.py`'s `reason_over_pieces()` creates its own
   trivial `TemporalWorking` for EVERY retrieved normative piece that
   carries a `temporal_applicability` tag (the `else: # self-contained`
   branch and the `singles` loop both do this unconditionally) -- so
   "narrow citations to governing_piece" did nothing, because almost every
   retrieved piece becomes its own trivial "governing_piece" regardless of
   topical relevance to the query.
3. Root cause, in Phase 3: `HybridRetriever.retrieve()` in
   `retrieval/hybrid_search.py` (see its own docstring, step 7: "Truncate
   to top_k") always returns exactly `top_k` pieces (default 10) with NO
   floor on relevance -- it pads out to top_k regardless of how low a
   piece's `rerank_score` is. Retrieval, CRAG sufficiency grading, temporal
   reasoning, and generation all then treat "made it into the top_k" as
   "belongs in the answer," with nothing anywhere checking "is this
   actually on-topic for what was asked."

## Why we're fixing it here, not downstream

Patching generation (filter what gets narrated/cited after the fact) would
work but treats the symptom. The actual defect is that retrieval hands
everything downstream a padded-out candidate set with no relevance floor.
Fixing it in Phase 3 means CRAG grading, temporal reasoning, and generation
all get a cleaner, more honestly-relevant piece set for free, instead of
each of them needing their own bolted-on relevance filter.

## Proposed fix (confirm/adjust against Phase 3's own design intent)

`retrieve()` already computes `rerank_score` per piece via
`FlashRankReranker`/`MockReranker` (`retrieval/reranker.py`) -- a
cross-encoder relevance score between the query and that specific passage.
Nothing currently reads that score to decide inclusion; it is only
attached for downstream visibility. Proposal: make `top_k` a ceiling, not
a fixed target -- after reranking, drop pieces whose `rerank_score` falls
below some floor (either an absolute threshold, or relative to the
top-scoring piece for that query), THEN truncate to `top_k`. When no
reranker is supplied (the `--no-rerank` fallback path, `rerank_score is
None`), decide whether `fused_score` (RRF-based) can serve the same
purpose or whether that path should be explicitly documented as not
relevance-floored.

This needs calibration against real data, not a guessed constant -- pull
actual `rerank_score` distributions for a few golden-set queries (both
clearly single-topic ones like P-30 above, and genuinely multi-clause ones
like P-02/P-3a which legitimately need 2+ pieces) before picking a number,
so the floor doesn't cut a legitimate segmented-accrual pair.

## Constraints to respect (standing project rules)

- Phase 3 is currently `DONE` with real measured numbers already in
  PROJECT_PLAN.md's Results Ledger (M3 close: mean Context Precision@10 =
  0.134, mean Context Recall@10 = 0.682, 18/38 at perfect recall, 4 at
  zero recall from the original probe-set run). Changing retrieval
  behavior invalidates those numbers -- `scripts/run_retrieval_harness.py`
  needs a real re-run after the fix, and PROJECT_PLAN.md needs an honest
  before/after entry (not a silent overwrite of the old numbers -- show
  the delta and why it changed).
- No performance number or capability claim goes anywhere without a real
  measured run recorded in the Results Ledger -- same standing rule as
  always.
- After the retrieval fix lands: the existing 167 unit tests need a
  re-run (some `tests/test_hybrid_search.py`/`test_crag_grader.py`/etc.
  fixtures may assume today's "always exactly top_k" behavior and could
  need updating, not just re-passing). Then T-5.3/T-5.4 (RAGAS +
  Citation Accuracy, both already fixed for their own separate bugs this
  session -- see commits `7ee0310`, `48daa40`, `a3f4b88`) need a fresh
  24-item run to get real numbers into the ledger -- nothing from the
  last two runs (0.106, then 0.151 mean Citation Accuracy) should be
  trusted or entered anywhere, both were against the pre-fix retrieval.
- Document the bug (found + root cause + fix) in PROJECT_PLAN.md's Phase 3
  detail section and the Change Log, same style as the existing entries
  (arithmetic gap, jurisdiction_scope, the two bugs from this session) --
  this project's interview-defensibility story is built on recording real
  bugs found and fixed, not hiding the fact that Phase 3 needed reopening.
- Real API-calling scripts (the retrieval harness, the eval scripts) run
  in Prashanth's own PowerShell terminal (`.venv-win`) -- this sandbox and
  the device bridge's Linux helper VM can't make live OpenAI calls or
  execute the Windows venv directly.

Please confirm the fix approach against Phase 3's original design
rationale (there may be a reason top_k was implemented as a fixed
truncation rather than a relevance-floored one worth revisiting), then
implement, test, and hand back to the Phase 5 session for the golden-set
re-run once retrieval is fixed and re-measured.
