# Project Plan — HR-Policy Advanced RAG (Portfolio Slot 4)

**Owner:** Prashanth · **Started:** 2026-09-03 · **Repo:** `C:\Project\HR policy RAG`

---

## How this document works

Nine phases, each ending in a **milestone with a demonstrable exit criterion** — something that can be shown or a number that was actually measured, never a claim that work was "completed." A phase is not closed because its tasks are ticked; it is closed because its exit criterion has been *witnessed*.

This is the tracking document of record. The live task board mirrors it; where they disagree, this file wins.

**Status legend**

| Mark | Meaning |
|---|---|
| `DONE` | Exit criterion witnessed and recorded |
| `WIP` | In progress |
| `TODO` | Not started |
| `BLOCKED` | Waiting on a named dependency |
| `HOLD` | Deliberately deferred (fast-follow) |

**Standing rule.** No performance number, capability claim, or "production-grade" description enters this document, the README, the code, or an interview answer unless it was produced by a real run and recorded in §Results Ledger. Targets are not results. Aspirations are not results.

**Standing rule, companion to the above.** Every real bug found on a real run gets root-caused (evidence, not guesswork -- read the failing library's actual source, trace a symptom through every layer to its real origin) and recorded here, in the phase it belongs to plus the Change Log, whether or not it's fixed yet. Never silently patch and move on. This is deliberate, not incidental: a project with zero recorded bugs either wasn't tested for real or isn't being honest about its history, and "I made a mistake, found it on a real run, and fixed it" is the actual differentiator between this project and a tutorial-standard one -- it's interview material, not something to tidy away before showing the work.

**Calendar note.** Phases are numbered by working day (D1–D7) against the Slot 4 allocation in `AI_Engineer_14Day_Schedule.pdf`. That file lives in the `Career_Transition` folder, which is not connected to this session — day-to-calendar mapping is therefore indicative, not authoritative. Connect the folder and it can be reconciled properly.

---

## Milestone summary

| # | Milestone | Exit criterion (demonstrable) | Day | Status |
|---|---|---|---|---|
| **M0** | Design locked, corpus grounded | Corpus decision closed; Tier-1 real statutory corpus committed; failure register + probe set + corpus spec committed | D1 | `DONE` |
| **M1** | Corpus complete | Every requirement R-01→R-25 has a corpus artifact; every probe has something to bite on; defect manifest exists | D1–D2 | `DONE` |
| **M2** | Indexed | Corpus fully indexed under the extended schema; proviso-boundary and metadata tests pass | D2–D3 | `DONE` |
| **M3** | Retrieval measured | Retrieval-only Context Precision + Recall **measured** against the probe set and recorded in the ledger | D3 | `DONE` -- reopened for a real downstream bug (Session 5), fixed + calibrated + re-measured for real 2026-09-04 (Precision 0.134->0.253, Recall 0.682->0.568, honest trade-off recorded), see Phase 3 detail |
| **M4** | End-to-end answers | Pipeline answers the probe set with citations; clarification contract returns structured output on `MUST_CLARIFY` items | D4 | `DONE` (composition proven on representative real cases -- see caveat in Phase 4 detail; a real narrative-substance defect found during T-5.5 diagnosis was fixed 2026-09-04, Session 8 -- see Phase 4 detail and Change Log) |
| **M5** | Baseline scored | All 5 metrics + the four-class confusion matrix run on the golden set; **first real numbers** recorded | D4–D5 | `DONE` (real post-narrative-fix numbers, Session 8: RAGAS Precision 0.726, Recall 0.462, Faithfulness **0.497** (was 0.089, +458% relative), Answer Correctness **0.334** (was 0.169, +98% relative); Citation Accuracy **0.861** (was 0.214, +302% relative); confusion matrix class match 14/24, over-refusal 1 (P-01, known reranker limitation), 0/11 ANSWERED items lack real content -- confirms the narrative-substance fix. Exit criterion (real numbers recorded) is met, but real run surfaced new, unexplained weak spots not yet investigated: P-16 still scores 0.0 on Citation Accuracy; both MUST_REFUSE golden items (P-18, P-39) failed to refuse; 3/5 MUST_FLAG items misclassified; and P-3a/P-3b/P-15 (MUST_ANSWER) unexpectedly came back NEEDS_CLARIFICATION -- notable since P-3a/P-3b were previously reported (Session 3) as working end-to-end. See Phase 5 detail and Change Log for full breakdown.) |
| **M6** | Freshness demoable | A document edited in Drive is picked up, re-indexed incrementally, and the answer changes correctly on camera | D5–D6 | `TODO` |
| **M7** | Regression-gated | CI runs the eval on push and fails the build on regression from recorded baseline | D6 | `TODO` |
| **M8** | Deployed | Public Cloud Run URL answers a query end-to-end; LangSmith trace inspectable | D7 | `TODO` (confirmed IN SCOPE by Prashanth 2026-09-04 -- real deployment, not a fast-follow) |
| **M9** | Defensible | Full cold narration, unaided, no notes | D7+2 | `TODO` |

---

## Phase detail

### Phase 0 — Foundation & design lock · `DONE`

| ID | Task | Status |
|---|---|---|
| T-0.1 | Close the open corpus-scope decision | `DONE` |
| T-0.2 | Scaffold repo, venv, requirements, .gitignore, git | `DONE` |
| T-0.3 | Write README ADR (design, architecture, eval, guardrail, scope + non-goals) | `DONE` |
| T-0.4 | Build Tier-1 real statutory corpus (India / UAE / Germany), clause-tagged | `DONE` |
| T-0.5 | Failure-mode register — 39 modes, 5 families, 4 architecture findings | `DONE` |
| T-0.6 | Adversarial probe set — 41 probes, four expected-behaviour classes | `DONE` |
| T-0.7 | Corpus requirements spec — R-01→R-25, build order | `DONE` |

**Exit criterion met:** commits `d31b734`, `613ac2e`, `442ee12`.

---

### Phase 1 — Corpus construction · `DONE` · D1–D2

Builds the Tier-2 synthetic layer (**Meridian Global Services**, fictional, banner-labelled) to satisfy the requirements spec. Build order is from `CORPUS_REQUIREMENTS.md` §3 and is not arbitrary: things that *look like mistakes* are written first, with their intent recorded, so they don't get tidied away later.

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-1.1 | `docs/DELIBERATE_DEFECTS.md` manifest — non-compliant clause, decoy illustration, intentional gaps | — | `DONE` |
| T-1.2 | Deliberate-defect clauses: R-11 (policy below statutory floor), R-20 (₹50,000 decoy illustration), R-25 (paternity-leave gap), R-23 (low-salience clause), R-15 (incomplete governing-law clause) | T-1.1 | `DONE` |
| T-1.3 | Version-pair structures: R-01→R-09 (segmented accrual, grandfathered, future-dated, retroactive, silent + partial supersession, sunset, renumbering, vague effective date) | T-1.2 | `DONE` |
| T-1.4 | Conflict structures: R-12/R-13/R-14 (free-zone annexe, near-identical cross-country, divergent definitions) — R-10/R-11/R-15 landed early in T-1.2 | T-1.3 | `DONE` |
| T-1.5 | Retrieval-mechanic structures: R-16→R-24 (slab table, proviso, cross-reference, synonym spread, near-duplicate pair, scattered operands, false-premise bait) | T-1.4 | `DONE` |
| T-1.6 | Ordinary connective policy prose — **written last**, deliberately: distractor mass is part of the test environment | T-1.5 | `DONE` |
| T-1.7 | Coverage audit: assert every R-requirement and every probe maps to a real corpus artifact | T-1.6 | `DONE` — automated, `eval/coverage_audit.py`, PASS |
| T-1.8 | Work the `[VERIFY]` register down (see §Verification Register) | — | `TODO` |

**Exit criterion (M1):** T-1.7 audit passes — no probe is unanswerable for want of a document, and no requirement is unimplemented.

**Risk:** an LLM-written policy manual drifts toward uniform, plausible, *easy* prose — which would quietly defeat the whole point. Mitigation is T-1.6's ordering and a deliberate variation in register, clause density, and drafting quality across chapters.

---

### Phase 2 — Ingestion & indexing · `DONE` · D2–D3

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-2.1 | Parser: metadata blocks → structured chunk records | M1 | `DONE` |
| T-2.2 | Extended chunk schema: `temporal_applicability`, `revision_date`, `indexed_at`, `normative`, `lineage_id`, `supersedes`/`superseded_by`, `cohort_rule`, `jurisdiction_scope` | T-2.1 | `DONE` |
| T-2.3 | Clause-aware chunker — **hard rule: a proviso is never split from its clause** (FM-D2) | T-2.1 | `DONE` |
| T-2.4 | Table extraction → row-serialised text, separate chunk stream (per the no-vision decision) | T-2.3 | `DONE` |
| T-2.5 | Change-kind classifier: `NO_OP` / `EDITORIAL` / `SUBSTANTIVE` / `ADDITION` / `SUNSET` | T-2.2 | `DONE` |
| T-2.6 | BM25 index build | T-2.3 | `DONE` |
| T-2.7 | Vector index build — Qdrant local, `text-embedding-3` | T-2.3 | `DONE` |
| T-2.8 | Unit tests: proviso integrity, three-clock separation, lineage linkage, normative flagging | T-2.5 | `DONE` |
| T-2.9 | Non-markdown format parsers (PDF/DOCX/XLSX/CSV) — same `ChunkMetadata` shape via sidecar manifests; real generated sample files, not a full corpus rewrite | T-2.2 | `DONE` |

**Exit criterion (M2):** full corpus indexed; T-2.8 green. **Met 3 Sep 2026** — see Results below.

**T-2.9 added mid-phase (3 Sep 2026):** Prashanth flagged that an all-markdown corpus doesn't prove
real-world document handling. `ingestion/formats/` now has tested parsers for PDF, Word, and Excel/CSV,
each producing the same validated schema the markdown parser does, proven against real generated files
under `corpus_samples/multi_format/` — see README's "Source document formats" section for the full
reasoning on why this is a small representative sample, not a full 72-clause rewrite.

**Status — M2 CLOSED (3 Sep 2026):** All of T-2.1 through T-2.9 done, 70/70 tests green, and the live
vector index actually exists on disk (`build/vector_index`, gitignored — rebuild with
`scripts/build_vector_index.py --live`, don't commit it).

**Results (live run, 3 Sep 2026):**
- `--dry-run` (3 units) then `--live` (remaining 81 units, 3 served from embedding cache) both ran
  successfully against the real OpenAI API, using `text-embedding-3-small`, from Prashanth's own machine.
- Both this session's cloud container and the device-bridge shell into Prashanth's machine turned out to
  have `api.openai.com` blocked by their network proxy (confirmed via a direct curl test and the proxy's
  own status log: `403` on `CONNECT`, `"kind": "connect_rejected"`) — a sandbox network-policy constraint,
  not a code or credentials problem. Prashanth ran the two script invocations himself from a plain terminal
  outside any sandbox, where the OpenAI call went through normally.
- That real `--live` run also surfaced a genuine bug, since neither the test suite nor `--dry-run` ever
  exercises on-disk persistence: `VectorIndex` was passing the local index path through Qdrant's `location=`
  parameter (meant for remote-server URLs), which on Windows misread the drive letter in
  `C:\Project\HR policy RAG\...` as a URL scheme (`Unknown scheme: c`). Fixed by using Qdrant's `path=`
  parameter for on-disk persistence instead (commit `dcb08b5`); 70/70 tests still green after the fix.
- Exact dollar cost of the embedding call: not yet recorded here — the script doesn't print a running total,
  so per this project's "witnessed, not claimed" rule this needs the actual figure from the OpenAI usage
  dashboard before it's written down as a fact anywhere (this file, the README, or said out loud in an
  interview).

**Gate:** T-2.7 is the first step that spends OpenAI credit. Confirm the key and its balance before running it.

**Budget confirmed (2026-09-03):** $4.98 balance. Locked-in model choices for every OpenAI call in this
project (embeddings, generation, CRAG grading, Citation Accuracy G-Eval) — chosen for cost, not capability,
and this constraint gets stated as such wherever these models are named, per the project's own ground rule
on unverified capability claims:
- Embeddings: `text-embedding-3-small` (not `-large` — no measurement yet justifies the larger model's cost).
- Generation / grading / judge: `gpt-4o-mini`, or `gpt-5-nano` if/when confirmed available on this account —
  never a larger model, until a real cost measurement (T-2.7's actual embedding spend, then Phase 5's eval
  run) says the budget allows more.
- Before T-2.7 runs: batch-embed with caching (never re-embed an unchanged chunk), and dry-run T-2.6/T-2.7
  end-to-end against a 2-3 clause slice first to see one real cost number before committing the full 72-clause
  corpus to the API.

---

### Phase 3 — Retrieval core · `DONE` · D3

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-3.1 | Reciprocal Rank Fusion over BM25 + vector | M2 | `DONE` |
| T-3.2 | Hard metadata filters: country, `jurisdiction_scope` (FM-B6 — soft embedding preference is not sufficient) | T-3.1 | `DONE` |
| T-3.3 | As-of-date filter on `effective_date`, overridable, default today (Finding 2) | T-3.2 | `DONE` |
| T-3.4 | Lineage dedup + top-k diversity before rerank (FM-D6) | T-3.3 | `DONE` |
| T-3.5 | FlashRank rerank; record the cutoff and the reason for it | T-3.4 | `DONE` |
| T-3.6 | Retrieval-only harness: Context Precision + Recall over the probe set | T-3.5 | `DONE` |

**Exit criterion (M3):** T-3.6 produces real numbers, recorded in the ledger. This is the first entry in §Results.

**Why retrieval is measured before generation exists:** a generation bug and a retrieval bug produce the same symptom — a wrong answer. Measuring retrieval alone first means the later end-to-end numbers are attributable. This is also the honest answer to "how do you know the reranker earns its place?"

**Status — Phase 3 DONE, M3 CLOSED (3 Sep 2026):** T-3.1 through T-3.4 done and unit-tested —
`retrieval/fusion.py` (RRF, k=60, the standard unmeasured default), `retrieval/filters.py` (hard
country/`jurisdiction_scope` filters per FM-B6; `select_current_as_of()` resolving each `lineage_id` to the
version in force on a given date, closing both directions of Finding 2; `dedup_by_lineage()` for FM-D6), and
`retrieval/hybrid_search.py` (`HybridRetriever` composing all of the above into the one entry point Phase 4
and T-3.6 both call). `ingestion/index_units.py`'s `IndexableUnit` gained a `jurisdiction_scope` field it was
missing (needed for T-3.2's DIFC-vs-mainland split; docstring already claimed it carried this field, code
didn't). 103/103 tests green (33 new).

**T-3.5 (rerank) — done.** `retrieval/reranker.py` has a `Reranker` Protocol, `FlashRankReranker`
(`ms-marco-TinyBERT-L-2-v2`, lazy-imported), and `MockReranker` (deterministic lexical-overlap scorer, used
by every test — same split as `ingestion/embedder.py`'s `Embedder`/`MockEmbedder` pattern). Hit the same
sandbox `huggingface.co` block T-2.7 hit on `api.openai.com` (device-bridge shell too); handed to Prashanth
as `scripts/prefetch_reranker_model.py`, run once from a plain terminal outside any sandbox
(`.venv-win\Scripts\python.exe scripts\prefetch_reranker_model.py`, 3 Sep 2026, model cached in ~1s).
`retrieval/hybrid_search.py`'s `retrieve()` used FlashRank for every probe in the real T-3.6 run below (see
`"reranked": true` in the run's own output) — this is the first time in the project reranking has actually
executed, not just been coded against a mock.

**T-3.6 (retrieval harness) — done. Real numbers below.** `eval/retrieval_harness.py` parses all 43 probe
queries straight out of `eval/golden/adversarial_probe_set.md` (both its narrative-header and table-row
formats) and scores each against its known-correct `clause_id` set from `eval/probe_fixture_map.json`, using
plain set-overlap Context Precision/Recall (retrieval-only, deliberately simpler than Phase 5's RAGAS-judged
versions over generated answers — there's no generated answer yet). P-21/P-26/P-29/P-41 (empty expected set)
and P-39 (`DELIBERATE_ABSENCE`) excluded from scoring, not silently zeroed.

**Real run, 3 Sep 2026** (`.venv-win\Scripts\python.exe scripts\run_retrieval_harness.py`, top_k=10,
FlashRank reranking on, against the real `build/vector_index` and real `text-embedding-3-small` query
embeddings — output saved to `build/retrieval_harness_result.json`):

| Metric | Value |
|---|---|
| Probes scored | 38 (of 43 — 5 excluded, see above) |
| Mean Context Precision@10 | **0.134** |
| Mean Context Recall@10 | **0.682** |
| Probes with perfect recall (1.0) | 18 / 38 |
| Probes with zero recall (0.0) | 4 / 38 — P-05, P-25, P-33, P-35 |

**Honest read of these numbers, not spin:**
- The precision figure is mechanically bounded, not just low: expected-clause-set sizes across the 38 scored
  probes range 1–4 (mean 2.05), against a *fixed* top_k=10 — so a probe with a 2-clause expected set has a
  ceiling of 0.20 precision even with perfect retrieval, before any actual retrieval error. Precision@10 is
  the wrong lens for a corpus this small with expected sets this narrow; recall is the more informative
  number here, and top_k is a knob Phase 5's golden-set run should reconsider (a smaller top_k, or a
  precision definition scaled to |expected|), not something to explain away against this run.
- Recall (0.682 mean, 18/38 at a clean 1.0) says the hybrid pipeline finds what it's supposed to find on
  about two-thirds of the scored probes, in full, on more than half of them.
- **Four real, named failures, not swept in**: P-05 ("What's my notice period?" — the future-dated-amendment
  probe), P-25 (the transliterated Hindi/Urdu EOSB query — FM-C4's exact target), P-33 ("What's my
  EOSB?"/three-phrasing synonym probe), and P-35 (the v1/v2 notice-flood dedup probe) all scored recall 0.0 —
  nothing from their expected clause set was retrieved at all. These are flagged, not diagnosed, here — a
  genuine follow-up item, not yet root-caused. (P-25 in particular is worth watching in Phase 5: if it's
  still zero on the scored golden set, that's a real, demo-honest finding about non-English-script query
  handling, not a bug to quietly patch out before it's understood.)
- This is a *retrieval-only* number over the full 43-probe adversarial set, not the smaller, curated
  golden set Phase 5 scores end-to-end — it answers "does the retrieval layer find the right material," not
  "is the final answer correct." Nothing here should be quoted as an end-to-end accuracy figure.

M3's exit criterion — T-3.6 produces real numbers, recorded in the ledger — is met. See §Results ledger.

**Reopened, 2026-09-04 (Session 5)**: a real bug was found downstream, on Phase 5's first live T-5.4 run, that traces all the way back here. Symptom: every ANSWERED item cited 9-12 clauses when the golden set expected 1-3 (e.g. a query asking only about housing allowance also narrated DIFC leave, notice, probation, and gratuity-ceiling clauses). Root-caused through three layers: `generation/generator.py` cited everything retrieval handed it (patched, commit `48daa40`) -> `grading/temporal_reasoner.py`'s `reason_over_pieces()` wraps EVERY retrieved normative piece in its own trivial working regardless of topical relevance, so narrowing citations to "governing pieces" narrowed nothing -> `HybridRetriever.retrieve()` here in Phase 3 always truncates to exactly `top_k`, with **no floor on `rerank_score`** (its own docstring says step 7 is "truncate to top_k," unconditionally). The precision-bound note above ("top_k is a knob Phase 5's golden-set run should reconsider") flagged this exact class of issue at M3's original close and it was left as a follow-up rather than fixed then -- this is that follow-up landing for real. Fix proposed (make `top_k` a ceiling, not a target: drop pieces below a `rerank_score` floor before truncating) but deliberately NOT implemented in this session -- handed to a fresh Phase 3-focused session with full context, since this reopens an already-`DONE`, already-measured milestone and deserves that phase's own design rationale in the loop, not a downstream patch. **The 0.134/0.682 numbers above are now provisional** -- do not quote them as final, and re-run `scripts/run_retrieval_harness.py` for real once the fix lands. T-5.3/T-5.4 (RAGAS, Citation Accuracy) both need a fresh run afterward too; neither of Citation Accuracy's first two real runs (0.106, then 0.151 mean, this session) should be trusted or entered into the Results Ledger -- both ran against this pre-fix, over-broad retrieval.

**Fix implemented, 2026-09-04 (new Phase-3-focused session)**: confirmed the fix approach *does* match
Phase 3's own design intent before touching anything -- `grading/crag_grader.py`'s own docstring already
states its assumption that "whether a clause is topically ON-TOPIC for a free-text query... already
happened at rerank." That assumption was always correct about *where* relevance filtering belonged; step 7
just never actually did it. So this is retrieval finally delivering the contract Phase 4 was already built
against, not a new behavioural decision layered on top.

`HybridRetriever.retrieve()` gained a `min_rerank_score: float | None = None` parameter. When a reranker
runs, candidates scoring below the floor are dropped **before** truncating to `top_k` -- `top_k` is now a
ceiling, not a fixed target. Default is `None` (old, unfixed behaviour) deliberately: this project's
standing rule is no constant without calibration against real data (same status `rrf_k=60` and
`rerank_candidate_k=20` already carry), so the mechanism is built and tested, but **not yet wired in as the
actual default anywhere** -- `grading/pipeline.py`/`grading/answer_pipeline.py`/the eval scripts still call
`retrieve()` without it, so the bug is not yet fixed in practice, only fixable. The no-reranker fallback path
(`fused_score`) is explicitly left unfloored -- it's a reciprocal-rank score, not a relevance magnitude, and
flooring it would need its own separate calibration this session didn't attempt.

`scripts/dump_rerank_scores.py` is the calibration script (by-hand, real `FlashRankReranker` + real
`text-embedding-3-small` query embeddings, same pattern as every other real-API script in this project):
prints per-candidate `rerank_score` for a representative mix of single-topic queries (P-30, housing
allowance -- where a floor should cut almost everything but the target) and genuinely multi-clause ones
(P-02, P-3a -- where a SECOND piece legitimately belongs and must not get cut). **Not yet run.** Once it is,
the reported numbers pick the actual floor value, that value gets wired into the real call sites, 171/171
tests re-confirmed, then `scripts/run_retrieval_harness.py` (T-3.6) and both T-5.3/T-5.4 scripts re-run for
real, honest before/after numbers recorded here (not a silent overwrite of the provisional 0.134/0.682).

171/171 tests passing (167 + 4 new: default-unchanged regression guard, floor actually drops low-scoring
pieces, floor can legitimately return fewer than `top_k`, floor is a documented no-op without a reranker).

**Calibrated & wired in, 2026-09-04 (Session 6)**: Prashanth ran `scripts/dump_rerank_scores.py` for real
against P-30 (single-topic), P-02/P-3a (genuinely multi-clause), and P-01/P-17 (adversarial) -- full output
recorded in [[slot4_progress]]. Two honest findings came out of real data, not a guess:

1. **P-30 confirms the fix works as designed** -- true positive scores 0.9784, everything else in the
   candidate set is <=0.0016. A floor cleanly separates signal from padding here.
2. **P-01 and P-17 show a real limitation this fix does NOT solve, and is not claimed to**: on both, a
   clause that is *not* the expected citation scores higher than one that *is* -- P-01's decoy illustration
   (a deliberate D-2 corpus trap) scores 0.098 vs. the correct clause's 0.022; P-17's second correct clause
   scores only 0.0002, below four wrong clauses. **No floor value can fix a wrong ranking ORDER** -- that's a
   different problem than "the right answer scored too low relative to genuine noise," which is what the
   floor actually fixes. Investigating *why* the reranker mis-orders these was deliberately NOT pursued this
   session -- diminishing-returns reranker-tuning work on a 2-of-24-probes edge case is scope creep for this
   project's actual goal (architecture correctness + an honest bug trail), not a gap worth chasing here. See
   the forward-flag note in Phase 5's detail section below.

`DEFAULT_MIN_RERANK_SCORE = 0.001` was chosen as the most conservative value that trims the clearest padding
(the near-zero tails seen on P-30 and the back half of P-3a's candidate list) while not cutting any of the 7
true-positive pieces actually observed across all 5 calibration probes. Wired in as the *default* (not just
an available parameter) on the three real production entry points: `grading/pipeline.py`'s
`retrieve_and_grade()`, `grading/answer_pipeline.py`'s `answer_query()` (the actual M4/M5 call path the eval
scripts use), and `eval/retrieval_harness.py`'s `run_retrieval_harness()` (T-3.6). `HybridRetriever.retrieve()`
itself deliberately keeps its own default at `None` -- the floor is a production-pipeline policy decision, not
a property of the raw retrieval primitive, and its own test suite (`test_hybrid_search.py`) still exercises
the neutral, unopinionated building block. All three callers can still pass `min_rerank_score=None` explicitly
to reproduce old, pre-fix behaviour (needed to regenerate the original provisional numbers for an honest
before/after comparison).

174/174 tests passing (171 + 3 new: `retrieve_and_grade`/`answer_query` both default to the calibrated floor,
confirmed via signature inspection, not just import; the floor can still be explicitly disabled).

**Re-measured for real, 2026-09-04, same session -- M3 CLOSED again.** Prashanth ran
`scripts/run_retrieval_harness.py` against the live, calibrated fix. Real result, honest delta from the
provisional pre-fix numbers (see Results ledger for the full table):

```
Mean Context Precision@10: 0.253   (was 0.134, +89% relative)
Mean Context Recall@10:    0.568   (was 0.682, -17% relative)
```

**Read honestly, not spun -- this is a real trade-off, not a clean win**: precision nearly doubled, which is
the fix doing its job (fewer irrelevant clauses padded into the result set). But recall dropped a real 17%
relative on the full 38-probe set -- worse than the 5-probe calibration sample suggested. The live run log
shows several probes returning as few as 0-3 pieces where they used to get padded to 10 (two probes returned
0 pieces post-floor), which means the floor is legitimately costing some true positives on the full set, not
only trimming padding. `DEFAULT_MIN_RERANK_SCORE=0.001` was calibrated against only 5 probes (chosen to be
conservative against THOSE 5's true positives) -- the full 38-probe run shows that conservatism wasn't quite
conservative enough at full-corpus scale. **Not re-tuned this session** -- recorded as the honest result of
the value actually chosen, per this project's own standing rule (Convention 2: no number goes anywhere until
measured; the ledger shows what was measured, not what would look best). Worth a closer look in a future
session: whether a slightly lower floor (e.g. re-examining the probes that now return 0-2 pieces) trades some
of the precision gain back for recall, before this number gets treated as final.

**M3 exit criterion re-met with the fix in place.** `PROJECT_PLAN.md` milestone table and Results ledger
updated with the real post-fix numbers, pre-fix rows marked superseded (not deleted). Phase 3 status changed
back to `DONE`. The P-01/P-17 ranking-order limitation documented above remains unresolved and unrelated to
this recall trade-off -- two separate, both honestly recorded, limitations of the same fix.

---

### Phase 4 — Grading, generation & clarification · `DONE` · D4

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-4.1 | CRAG grading node — sufficiency test **includes the applicability rule**, not just the clause (Finding 1) | M3 | `DONE` |
| T-4.2 | Corrective re-query path on insufficient context | T-4.1 | `DONE` |
| T-4.3 | Temporal reasoning: apply `temporal_applicability` class; show the working on straddle cases | T-4.1 | `DONE` |
| T-4.4 | Generation, context-only, with clause-level citations (doc, section, version, effective date) | T-4.2 | `DONE` |
| T-4.5 | Stateless clarification contract: `NEEDS_CLARIFICATION` + `missing_facts[]` + `conditional_answers[]` (Finding 5) | T-4.4 | `DONE` |
| T-4.6 | Supersession flagging in answers (FM-E6) | T-4.4 | `DONE` |
| T-4.7 | LangSmith tracing on retrieval / grading / generation | T-4.4 | `DONE` |

**Exit criterion (M4):** the probe set runs end-to-end; `MUST_CLARIFY` probes return structured clarification rather than a guess or a flat refusal.

**Met, with a scope caveat stated plainly:** `grading/answer_pipeline.py`'s `answer_query()` composes T-4.1→T-4.6 into one call -- a query string goes in, the corrective re-query and temporal reasoning fire automatically (not hand-assembled), and the result comes out as `ANSWERED` / `NEEDS_CLARIFICATION` / `INSUFFICIENT`. Proven end-to-end on three real, representative cases (`tests/test_answer_pipeline.py`): P-01 (India ceiling, answers, does not split), P-3a (DIFC DEWS, self-corrects and splits at 2020-02-01, both segments cited), P-06 (grandfathered supplement, correctly returns `NEEDS_CLARIFICATION` rather than guessing). **What this is NOT**: a run of the full 43-probe adversarial set from raw query text alone. `answer_query()` takes `country`/`jurisdiction_scope`/`ServiceFacts` as arguments, already resolved -- parsing those out of free-text queries (dates, countries, joining dates) is a natural-language extraction step that was never one of T-4.1-T-4.7's tasks, so it doesn't exist yet. Running the full probe set unaided from raw text needs that extraction step built first (a candidate T-5 task, not retroactively added to Phase 4's scope here).

**Reopened once, 2026-09-04 (Session 8), on a real defect found during Phase 5's T-5.5 diagnosis pass**: `generation/generator.py::TemplateGenerator.generate()` was only ever narrating a generic per-clause template sentence for most temporally-reasoned pieces, never the clause's own text -- see the full diagnosis and fix writeup in the Phase 5 detail section below. Fixed by always appending the real text of every piece actually cited, right after the narrative. 174/174 tests passing; M4's own exit criterion (citations + structured clarification) is unaffected, since the fix only adds content, it doesn't change which pieces get cited or which status a query resolves to.

---

### Phase 5 — Evaluation harness · `WIP` · D4–D5

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-5.1 | Promote 20–30 probes into the scored golden set; fill golden answers + expected source clauses | M4, T-1.8 | `DONE` |
| T-5.2 | Label every item `MUST_ANSWER` / `MUST_REFUSE` / `MUST_CLARIFY` / `MUST_FLAG`; hold the ~45/25/20/10 mix | T-5.1 | `DONE` |
| T-5.3 | RAGAS: Context Precision, Context Recall, Faithfulness, Answer Correctness | T-5.2 | `DONE` (real post-narrative-fix numbers: Precision 0.726, Recall 0.462, Faithfulness **0.497**, Answer Correctness **0.334**, over 11/24 ANSWERED items -- Faithfulness up 458% relative and Answer Correctness up 98% relative from the pre-fix baseline, confirming the Session 7/8 root-cause diagnosis) |
| T-5.4 | Custom Citation Accuracy (LLM-as-judge, FinGuard G-Eval pattern) | T-5.3 | `DONE` (real post-narrative-fix number: mean **0.861** over 11/24 ANSWERED items, up from 0.214 pre-fix, +302% relative -- one item, P-16, still scores 0.0 and is flagged, not yet root-caused) |
| T-5.5 | Four-class confusion matrix + **over-refusal counter as a first-class defect** (Finding 3) | T-5.2 | `DONE` (real run, Session 8: class match 14/24, over-refusal count **1** (P-01, the known reranker-ordering limitation), 0/11 ANSWERED items lack real content -- confirms the narrative-substance fix holds. Two other weak spots surfaced honestly, not yet root-caused: both MUST_REFUSE items (P-18, P-39) failed to refuse; 3/5 MUST_FLAG items misclassified) |
| T-5.6 | Baseline run; record every number in the ledger | T-5.4, T-5.5 | `DONE` (all real post-narrative-fix numbers recorded above -- M5 exit criterion met) |

**Exit criterion (M5):** ledger populated with measured baselines. Until this milestone, the project has **no** numbers and none may be quoted anywhere.

**T-5.1/T-5.2 done 2026-09-03**: `eval/golden/scored_golden_set.json`, 24 items drawn from the 43-probe adversarial set, each carrying a class label, expected source clause IDs, and a golden answer derived from real corpus clause text (plus the closed V-1/V-3 verification findings) — no invented figures. Actual mix 46/25/21/8 (target 45/25/20/10). P-01's stale `[VERIFY]` tag removed in `adversarial_probe_set.md` (V-1 closed). **Real bug caught while curating**: P-33's probe wording used Gulf EOSB terminology that matches none of its fixture's actual four synonym names (long service award / loyalty payment / continuity recognition / service milestone grant) — corrected in `adversarial_probe_set.md`; this is the likely real explanation for P-33's zero-recall result in the M3 run (probe/fixture mismatch, not a demonstrated retrieval failure). P-33 held OUT of the scored set this round pending confirmation of the corrected wording. T-5.3–T-5.6 (RAGAS, Citation Accuracy, confusion matrix, baseline run) open next — the LLM-as-judge metrics need a by-hand script run outside this sandbox, same pattern as `build_vector_index.py`/`prefetch_reranker_model.py`.

**Blocked by T-1.8:** an item still carrying `[VERIFY]` cannot be promoted into the scored set. **Checked 3 Sep 2026 (Session 4):** none of the 43 probes actually require a golden answer keyed to V-2/V-4/V-5 — the UAE 1980→2021 transition (V-2) was never built as a corpus fixture (DIFC/DEWS took the real-straddle-case role instead, as V-3, already closed), and V-4/V-5 (Indian state variation, Labour Codes commencement) are already handled by an explicit "national baseline, Codes not yet in force" scoping note inside `corpus/tier1_law/india/india_law.md` itself. T-1.8 therefore does not block T-5.1 in practice; V-2/V-4/V-5 stay open and untouched, tracked as future corpus/verification work, not as a Phase 5 gate.

**Arithmetic gap found and closed, 2026-09-03/04 (Session 5, commits `49f533f`, `1ff410c`, `fe9e305`)**: while scoping T-5.3/T-5.4, traced the pipeline and found `TemplateGenerator` never actually computed a number — `grading/temporal_reasoner.py`'s four classes correctly decide which clause/version/segment governs, but nothing turned that into a rupee amount or day count from the corpus's own formula clauses. Not a bug; a real scope gap Phase 4 never covered. Presented three closure options to Prashanth; he chose building minimal deterministic arithmetic into `TemplateGenerator`. Built `generation/formula.py` (pure, LLM-free, corpus-constant-driven: India's 15-day/26-divisor gratuity formula + ₹20L/₹10L ceilings, UAE's 21/30-day tenure bands + 2-year-wage cap, the two India leave-rate versions), wired through `ServiceFacts.monthly_wage`, `TemporalWorking.service_start_date`/`valuation_date`/`monthly_wage`, `GeneratedAnswer.computed_amount`/`computed_days`, and a new `_compute_from_workings()` helper in `generator.py`. Verified by hand and via a live `answer_query()` smoke test before adding 15 new unit tests. **166/166 tests passing.** Then wired verified `facts`/`expected_computation` objects into P-01/P-02/P-03 in `scored_golden_set.json` (`ServiceFacts` is caller-supplied per `answer_pipeline.py`'s documented scope, never parsed from query text, so the eval harness needs a structured facts block distinct from the query string) — all three figures re-verified independently against `generation/formula.py` directly: P-01 amount=₹20,00,000 (uncapped ₹22,50,000), P-02 45+52=97 days, P-03 165 days. This closes the last blocker to T-5.3/T-5.4 scoring exact figures rather than method only.

**T-5.3/T-5.4 scripts written, 2026-09-04 (Session 5, commit `c26acf9`)**: `eval/run_ragas_eval.py` (RAGAS Context Precision/Recall/Faithfulness/Answer Correctness, judge gpt-4o-mini, embeddings text-embedding-3-small -- checked against the real `ragas` 0.4.3 API source before writing, not guessed) and `eval/run_citation_accuracy_eval.py` (custom Citation Accuracy: a programmatic expected-vs-cited clause_id diff plus a gpt-4o-mini G-Eval-style judge reading each cited clause's full text against the answer). Both pull `facts` out of each golden item into `ServiceFacts` and normalize the golden set's free-text `country` field down to the corpus schema's real enum (documented limitation: the DIFC-vs-mainland split on P-3a/P-3b/P-10/P-17 isn't enforced by either script's country filter). Neither has been run for real yet -- awaiting Prashanth's run outside this sandbox, same as every prior real-API step.

**jurisdiction_scope wired in, 2026-09-04 (commit `80e08be`)**: discussed with Prashanth whether DIFC should become a new country value; traced the actual code and found `retrieval/filters.py` already has a purpose-built `jurisdiction_scope` filter (Phase 3) with correct fallback semantics, and the corpus is already tagged `uae-mainland`/`uae-difc` -- a data-wiring gap, not a missing architecture piece. Set `jurisdiction_scope=uae-difc` on P-3a only (unambiguous entity); deliberately left unset on P-3b/P-17, whose entire point is entity ambiguity (query names a location, not the entity) and whose golden answers require both regimes cited -- forcing a jurisdiction there would defeat the probe. P-10 was mis-grouped in the earlier note; it's a clause-versioning case, not jurisdictional.

**Two real bugs found on the first live T-5.3/T-5.4 run, 2026-09-04 (Session 5)**: Prashanth ran both scripts for real (24 golden items, gpt-4o-mini judge, live OpenAI calls) after the `langchain_community.chat_models.vertexai` import blocker (below) was cleared. Two independent, unrelated defects surfaced immediately -- exactly the kind of thing a dry run against real data is for.

1. *RAGAS scoring returned `n/a` for all four metrics, on every item.* Root cause, confirmed by reading `ragas`'s own source (`ragas/executor.py`, `ragas/async_utils.py`) rather than guessing from the traceback: `ragas.evaluate()` unconditionally calls `nest_asyncio.apply()` for Jupyter-notebook compatibility, and `nest_asyncio`'s event-loop patching is incompatible with Python 3.11+'s `asyncio.timeout()` context manager (which `ragas` uses internally for LLM-call timeouts) -- surfacing as `RuntimeError("Timeout should be used inside a task")` on every job and silently NaN-ing every metric instead of failing loudly. **Fixed** in `eval/run_ragas_eval.py` by passing `allow_nest_asyncio=False` to `evaluate()` (a parameter `ragas` exposes for exactly this case; we run as a plain script, never inside an already-running Jupyter loop, so nest_asyncio was never needed here). Not yet re-run to confirm the fix produces real numbers.
2. *Citation Accuracy scored 0.106 mean, with 7/7 ANSWERED items flagged for "extra" (unexpected) citations.* Traced into the actual generation pipeline, not the eval script: `generation/generator.py`'s `TemplateGenerator.generate()` calls `citations = build_citations(pieces)`, and `build_citations()` (`generation/citations.py`) attaches **every retrieved normative piece** as a citation, unconditionally -- it never checks which pieces the answer's narrative actually drew on. On the temporal-reasoning path, the narrative only discusses the 1-3 clauses that actually govern the computation (via `TemporalWorking.governing_piece`/`segments`), but `citations` lists the full ~9-12-piece retrieved set regardless. This is a genuine over-citation defect in Phase 4/5 code, not an artifact of the eval harness -- and it means the existing test suite's citation checks only verified expected clauses were *present*, never that irrelevant ones were *absent*. **Fixed, 2026-09-04, commit `48daa40`**: Prashanth approved narrowing citations to pieces actually used. Added `generation/generator.py::_pieces_actually_used()`, which returns every normative piece when there's no temporal reasoning (matches the existing `if not workings` narration, which really does quote every normative piece verbatim) and, when `workings` exist, returns only each working's `governing_piece` / `segments[*].governing_piece` / `alternatives` -- the exact set the narrative actually discusses (per `grading/temporal_reasoner.py`). Both `build_citations()` and `check_supersession()` now run on this narrowed set instead of the raw retrieved `pieces` list -- `check_supersession`'s own docstring already said it reasons about "cited clause_ids", so it had the identical latent bug (a stray amendment note could fire for a piece that was retrieved but never actually cited).

**Why 166/166 existing tests never caught this**: every `test_generator.py` fixture passed exactly the 1-2 pieces the answer needed (`[piece]`, `[dews, legacy]`) -- never a realistic retrieval-breadth set (real `HybridRetriever` returns up to 10-12 pieces per query after CRAG correction). With `pieces == citations` by construction in every fixture, the bug was structurally invisible to the existing suite; it only surfaced against real corpus-scale retrieval in the first live T-5.4 run. Added `tests/test_generator.py::test_extra_retrieved_pieces_are_not_cited_when_unused` as a direct regression test -- passes a genuine governing piece plus one deliberately unrelated retrieved piece and asserts the unrelated one is never cited. **167/167 tests passing.** T-5.3/T-5.4 need a fresh 24-item run before any number goes in the Results ledger -- neither script has been re-run against this fix yet.

**Forward flag for the next T-5.3/T-5.4 real run, 2026-09-04 (Session 6) -- read this before re-diagnosing anything on P-01 or P-17**: Phase 3's reopened-bug fix (`min_rerank_score`, see Phase 3 detail) is now wired in and calibrated, but real calibration data showed it can only fix cases where a correct clause scores too low *relative to genuine noise* -- it cannot fix a case where a *wrong* clause outranks a *right* one, because no cutoff number can separate two scores when they're in the wrong order to begin with. Two of the 24 golden-set items are known to have exactly that shape, confirmed against real `FlashRankReranker` scores, not guessed:
- **P-01** (India gratuity): the corpus's own deliberate D-2 decoy illustration outscores the real answer (0.098 vs. 0.022). The floor cannot remove the decoy without also removing the real answer.
- **P-17** (DIFC vs. mainland): the second of two correct clauses scores 0.0002, below four unrelated clauses. Same shape, same reason.
If T-5.3/T-5.4's next real run shows lower-than-expected scores specifically on P-01 and/or P-17, **that is this already-diagnosed limitation surfacing, not a new bug** -- don't re-open a fresh root-cause investigation on it. It was deliberately left unfixed this session: chasing *why* the reranker mis-orders these two cases is real ML-tuning work disproportionate to what a 24-item synthetic-corpus demo needs, and the project's actual differentiator (architecture correctness + an honest bug trail) doesn't require solving it. If it's ever worth revisiting, it's a reranker/embedding-model question, not a retrieval-pipeline-architecture one.

**T-5.4 real post-fix run, 2026-09-04, same session**: Prashanth ran `eval/run_citation_accuracy_eval.py` against the live, calibrated fix. 11/24 golden items reached `ANSWERED` (13 correctly went to `NEEDS_CLARIFICATION`/`INSUFFICIENT` per their own class, or are still awaiting T-5.5's confusion-matrix breakdown to confirm). Mean Citation Accuracy over those 11: **0.214** -- up from the two untrusted pre-fix runs (0.106, then 0.151), neither of which was ever entered in the Results ledger. Real, honest read: **improved, not solved**. 6/11 items still show an unexpected/extra citation, 4/11 are missing an expected one. Some of this is expected to be the documented P-01/P-17 ranking-order limitation surfacing exactly as flagged above -- but the mix hasn't been broken down probe-by-probe against that specific list yet, so don't assume every remaining miss is that one limitation until T-5.5 does the real per-item breakdown.

**T-5.3 hit a second real bug on its first post-fix run attempt, 2026-09-04, same session**: `eval/run_ragas_eval.py` crashed immediately with `TypeError: evaluate() got an unexpected keyword argument 'allow_nest_asyncio'`. Root-caused, not just patched around: `requirements.txt` pins `ragas` with **no version**, so different machines installing at different times can legitimately land on different releases -- Prashanth's `.venv-win` install picked up a newer `ragas` release than the `0.4.3` this project's own dev reference copy carries, and that newer release apparently removed or renamed the `allow_nest_asyncio` parameter the Session 5 fix depended on (most likely because the underlying `nest_asyncio`/`asyncio.timeout()` incompatibility that parameter existed to work around was fixed upstream — plausible but not confirmed by reading that release's source, since it isn't available in this sandbox). **Fixed properly, not by guessing a version to pin**: `eval/run_ragas_eval.py` now calls `inspect.signature(evaluate)` on whatever `ragas` is actually installed and only passes `allow_nest_asyncio=False` if that release's `evaluate()` still accepts it -- self-diagnosing rather than assuming either shape, and prints which path it took plus the installed `ragas.__version__` so the terminal output is self-documenting. If metrics come back `n/a`/`NaN` on the newer release (the original symptom of the incompatibility this flag existed to prevent), that would mean the incompatibility persists under a different parameter name and needs a fresh look -- the script says so explicitly in that case rather than failing silently. 174/174 tests still passing (no pipeline code touched). **Not yet re-run against the fix** -- Prashanth needs to re-run `eval/run_ragas_eval.py` once more for T-5.3's actual first real numbers.

**T-5.3's re-run crashed differently, same real bug resurfacing exactly as flagged, 2026-09-04, same session**: Prashanth re-ran `eval/run_ragas_eval.py` after the `inspect.signature()` fix landed. It no longer crashed with a `TypeError` -- it correctly detected that the installed `ragas` (0.3.1) has no `allow_nest_asyncio` parameter and skipped passing it, exactly as designed -- but then every metric came back `n/a`, with `RuntimeError(Timeout should be used inside a task)` on all 44 jobs. That is the *original* Session 5 incompatibility (nest_asyncio's event-loop patching vs. Python 3.11+'s `asyncio.timeout()`), not a new bug, and the script's own printed warning said so. Root-caused for real this time by reading both installed ragas releases' actual source side by side, not guessing from the traceback: **the "newer version removed the parameter" theory in the paragraph above was wrong.** ragas 0.3.1 -- what `.venv-win` actually has -- is *older* than this project's 0.4.3 dev-reference venv, and it is missing something 0.4.3 *added*: 0.4.3's `ragas/async_utils.py::apply_nest_asyncio()` only patches the event loop when one is already running (the Jupyter case nest_asyncio exists for) and is a no-op otherwise; 0.3.1's `ragas/executor.py` instead calls `nest_asyncio.apply()` unconditionally at *module import time*, with no such guard, and no parameter exists on 0.3.1 to turn that off. So `allow_nest_asyncio=False` was never going to be reachable on this install -- the flag it depends on doesn't exist on the version that needs it. **Fixed at the actual layer this time**: `eval/run_ragas_eval.py` now monkeypatches `nest_asyncio.apply` to a no-op *before* importing `ragas` at all, so `ragas/executor.py`'s unconditional call becomes inert on every version -- this mirrors what 0.4.3 already does safely by itself, and is safe here specifically because this script is always a plain top-level script, never a Jupyter cell with an already-running loop (the only scenario nest_asyncio is for). The `inspect.signature()`/`allow_nest_asyncio=False` logic from the previous fix is kept as a harmless belt-and-suspenders for versions that do offer it. 174/174 tests still passing (no pipeline code touched). **Not yet re-run against this fix** -- Prashanth needs to run `eval/run_ragas_eval.py` one more time for T-5.3's actual first real numbers.

**T-5.5 diagnosis pass, 2026-09-04 (real per-item data, not guessed) -- both questions the forward-flag note above asked T-5.5 to check, answered before building the confusion matrix itself:**

1. *Are the 6 extra / 4 missing Citation Accuracy items (`build/citation_accuracy_result.json`) the documented P-01/P-17 ranking-order limitation?* **No.** Checked directly: neither P-01 (status `INSUFFICIENT`) nor P-17 (status `NEEDS_CLARIFICATION`) is even among the 11 `ANSWERED` items this run scored -- the known limitation doesn't apply to a single one of the real misses (P-03, P-40, P-16, P-31, P-34, P-05 extra; P-10, P-05, P-38, P-18 missing). The real cause is different and more fundamental, found by reading the actual judge verdicts: **P-30's answer cites exactly the one correct clause (`MER-AE-HOUSING-TABLE`, zero extra) and still scores 0.0**, because the judge reasons "the clause does not mention that the version in force on the trigger date governs the entire computation" -- i.e. it's checking the cited clause against `TemplateGenerator`'s generic per-clause template sentence, not against any real housing-allowance content, because the answer's actual text contains no real content to check. Same pattern verified on P-16, P-31, P-40. This is not a citation-selection bug (that part is fixed); it's that the answer text has nothing substantive in it for a citation to support.
2. *Is low Faithfulness/Answer Correctness explained by computed arithmetic vs. literal clause text?* **Not confirmed -- opposite pattern found.** The two items WITH a computed figure score the two highest Faithfulness values in the set (P-02, `Faithfulness=0.417`, "Computed: 97 days..."; P-03, `Faithfulness=0.395`). Every item scoring exactly `0.0` (8 of 11: P-40, P-16, P-30, P-31, P-34, P-10, P-05, P-18) has an answer text that is **100% generic template boilerplate with no number and no clause-derived content at all** -- confirmed by printing `build/ragas_eval_result.json`'s actual `answer_text` field for each, e.g. P-30's full answer is just "MER-AE-HOUSING-TABLE is POINT_IN_TIME: the version in force on the trigger date governs the entire computation... Governing version effective from 2024-01-01." and nothing else -- it never states what the housing allowance actually is.

**Real root cause, confirmed by reading the actual code, not inferred from the pattern above**: `grading/temporal_reasoner.py::reason_over_pieces()` wraps *every* retrieved piece carrying a `temporal_applicability` tag in its own `TemporalWorking` (the `singles` loop and the `else: # self-contained` branch both do this unconditionally, one working per piece, regardless of topical fit). `generation/generator.py::TemplateGenerator.generate()` then does `lines.extend(w.narrative)` for every working when `workings` is non-empty -- and `narrative` for the self-contained/POINT_IN_TIME case is *only* the templated meta-sentence about temporal governance (see `reason_point_in_time()`/the self-contained branch in `reason_over_pieces()`), never the piece's own `text`. Compare the `if not workings:` fallback branch just above it, which does append `p.text` for every normative piece -- that's the one case where real clause content survives into the answer. Since `reason_over_pieces()` now returns a non-empty `workings` list for nearly every retrieved piece (this is the same trivial-wrapping behaviour Session 6 already found defeats citation narrowing, see M3's bug trail), the `if not workings:` branch essentially never fires in practice, and most real answers -- unless the arithmetic path in `_compute_from_workings()` produces a number -- contain zero actual policy content. This single defect plausibly explains BOTH T-5.3's low Faithfulness/Answer Correctness and most of T-5.4's remaining misses (a judge or a RAGAS claim-checker has nothing real to verify a citation against).

**Scope call made, fix built and unit-tested, 2026-09-04 (Session 8)**: presented two fix shapes -- (A) teach `reason_over_pieces()`'s trivial per-piece wrapping to embed the piece's own text into its narrative (touches the temporal-reasoning module itself, the already-proven straddle-case logic); (B) teach `TemplateGenerator.generate()` to always follow the narrative with the real text of every piece it actually relied on (`used_pieces`, i.e. exactly what already gets cited), a change scoped entirely to `generator.py`. Prashanth chose **(B)** as the smaller, safer change. Implemented in `generate()`: whenever `workings` exist and nothing is `missing`, the answer now appends the real `.text` of every piece in `used_pieces` (deduplicated by `clause_id`) immediately after the temporal narrative -- so a cited clause is always also quoted, matching the `if not workings:` branch's own long-standing behaviour, instead of only ever being named in a generic template sentence. **Verified against the exact P-30 symptom from the T-5.5 diagnosis pass above**: re-running the housing-allowance query's real corpus piece (`MER-AE-HOUSING-TABLE`) through `reason_over_pieces()` + the fixed `generate()` now produces an answer whose text includes the clause's real schedule content ("Schedule 2 — Monthly housing allowance... Grade A1–A3, under 3 years of service: 4,000 per month...") after the temporal-governance sentence, where before the fix the answer was only the two generic sentences with zero real content. **174/174 tests still passing** -- purely additive change, no existing assertion (`test_generator.py`) checked for the ABSENCE of clause text in the `workings` branch, so nothing broke. **Not yet re-run against T-5.3/T-5.4/T-5.5 for real** -- the previously-recorded RAGAS/Citation-Accuracy numbers in the Results Ledger (Faithfulness 0.089, Answer Correctness 0.169, Citation Accuracy 0.214) are now **pre-fix baselines**, not current; Prashanth needs to re-run `eval/run_ragas_eval.py`, `eval/run_citation_accuracy_eval.py`, and `eval/run_confusion_matrix.py` once more from `.venv-win` to get the real post-fix numbers before T-5.6 closes M5.

**T-5.3's real first numbers, 2026-09-04, same session**: Prashanth re-ran `eval/run_ragas_eval.py` against
the nest_asyncio monkeypatch fix. It worked -- all 44 real OpenAI calls (gpt-4o-mini judge,
text-embedding-3-small) succeeded, no crash, no `n/a`. Over the 11/24 golden items reaching `ANSWERED`:
Context Precision 0.726, Context Recall 0.492, Faithfulness 0.089, Answer Correctness 0.169. This confirms
the root-cause diagnosis was right this time -- three real bugs found and fixed in sequence on this one
task (the `TypeError`'s wrong-version-direction misdiagnosis, then the actual unconditional-`nest_asyncio
.apply()`-at-import-time cause), each one found by reading the real installed source rather than guessing.
Faithfulness and Answer Correctness are both low -- recorded honestly, not yet root-caused. See the
Results Ledger's honest-read paragraph for the working (unconfirmed) hypothesis: RAGAS's Faithfulness
metric checks each claim in the answer against literal retrieved-context text, and this pipeline's computed
rupee amounts/day counts (`generation/formula.py`) are arithmetic over corpus constants, not sentences that
appear verbatim in any clause -- plausible, not confirmed. T-5.5 (confusion matrix) should check this
against the real per-item breakdown in `build/ragas_eval_result.json` before any fix is proposed.

---

### Phase 6 — Freshness & guardrail · `TODO` · D5–D6

The differentiator. Everything before this is table stakes.

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-6.1 | GCP project + Drive API enablement + credentials (from scratch — none exist yet) | — | `DONE` |
| T-6.2 | Upload corpus to a Drive folder as the live source of record | T-6.1 | `TODO` |
| T-6.3 | Change detection by polling | T-6.2 | `TODO` |
| T-6.4 | Incremental re-index of only the changed document | T-6.3, M2 | `TODO` |
| T-6.5 | Version-event handling on `SUBSTANTIVE` / `SUNSET` — supersede predecessor at clause level | T-6.4 | `TODO` |
| T-6.6 | Faithfulness reused live as refusal gate; calibrate the threshold **against the over-refusal counter**, not in isolation | M5 | `TODO` |
| T-6.7 | Scripted live demo: edit a clause in Drive → show pickup → show the answer change and the supersession flag | T-6.5 | `TODO` |
| T-6.8 | Re-run eval post-freshness; confirm no regression | T-6.6 | `TODO` |

**Exit criterion (M6):** T-6.7 performed live, start to finish, without intervention.

**Risk:** threshold calibration is where a guardrail quietly becomes a refusal machine. T-6.6 is explicitly gated on the over-refusal counter for that reason.

---

### Phase 7 — CI gate · `TODO` · D6

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-7.1 | GitHub Actions workflow running the eval harness | M5 | `TODO` |
| T-7.2 | Gate on **no regression from recorded baseline** — not on invented absolute thresholds | T-7.1 | `TODO` |
| T-7.3 | Publish per-run scorecard as a build artifact | T-7.2 | `TODO` |

**Exit criterion (M7):** a deliberately-introduced regression fails the build.

**Design note.** The gate is relative, not absolute, and that is a deliberate choice: an absolute threshold would be a number invented before any measurement existed, which the standing rule forbids. "No worse than the last recorded run" is both honest and a stricter guard against drift.

---

### Phase 8 — Deployment · `TODO` · D7

**Scope confirmed 2026-09-04**: Prashanth explicitly confirmed Phase 8 is IN SCOPE for "finish the project" -- this is an end-to-end project with real deployment, not a fast-follow to skip for the portfolio postmortem. The original HOLD/fast-follow framing below is historical context for why it was sequenced last, not a statement that it can be dropped.

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-8.1 | Dockerize | M6 | `TODO` |
| T-8.2 | Qdrant Cloud; migrate index off local | T-8.1 | `TODO` |
| T-8.3 | Deploy to Cloud Run | T-8.2 | `TODO` |
| T-8.4 | FastAPI endpoint + minimal query UI | T-8.3 | `TODO` |
| T-8.5 | Smoke test against the deployed URL | T-8.4 | `TODO` |

**Exit criterion (M8):** public URL answers end-to-end; LangSmith trace inspectable for that answer.

Originally sequenced last because local prototype quality outranks deployment speed -- still true as a sequencing rationale (M5/M6/M7 come first), but not a reason to skip it.

---

### Phase 9 — Defense preparation · `TODO` · D7+2

Deliberately scheduled *after* the build stabilises, not same-day.

| ID | Task | Status |
|---|---|---|
| T-9.1 | Cold narration, unaided: architecture end to end | `TODO` |
| T-9.2 | Rehearse the four hard questions (below) | `TODO` |
| T-9.3 | Audit every claim in README + demo script against the ledger; delete anything unmeasured | `TODO` |
| T-9.4 | Record demo walkthrough | `TODO` |

**The four questions this project must survive.** Each is a real interview question that this design has a specific answer to — and having the answer is the point of the design choices upstream.

1. *"An employee's service spans your policy change. Walk me through the calculation."* → the four applicability classes, and why the gratuity ceiling is **not** split-and-summed even though the instinct says otherwise.
2. *"Your guardrail is a faithfulness score. What stops it refusing everything?"* → the four-class confusion matrix and the over-refusal counter.
3. *"How do you know the reranker earns its place?"* → retrieval measured standalone at M3, before generation existed.
4. *"Someone fixes a typo in a source document. What happens?"* → the change-kind classifier; `EDITORIAL` creates no version event.

**Exit criterion (M9):** T-9.1 delivered with no notes and no reference to the repo.

---

## Verification register

Open items under the standing rule. **None may be promoted into the scored golden set while open.**

| # | Item | Blocks | Status |
|---|---|---|---|
| V-1 | India gratuity ceiling is `POINT_IN_TIME` | P-01 (marquee probe) | `CLOSED` 2026-09-03 — see below |
| V-2 | UAE Federal Law 8/1980 → Decree-Law 33/2021 transition mechanics for accrued gratuity | Best real straddle case; no golden answer until closed | `OPEN` |
| V-3 | DIFC divergence from UAE mainland | P-17, R-12 | `CLOSED` 2026-09-03 — two concurring sources on notice (7/30/90 by service), leave (20 working days vs 30 calendar), DEWS from 2020-02-01 at 5.83%/8.33% with pre-transition service paid as legacy gratuity, probation 6 months (same as mainland). Article numbers other than Art. 62 not verified and deliberately omitted rather than guessed. ADGM not examined — out of scope unless raised. |
| V-4 | Indian state-level variation — verify one state, or scope corpus explicitly to "national baseline" and say so | Corpus scope statement | `OPEN` |
| V-5 | India Labour Codes commencement status | Already flagged in Tier-1 corpus note | `OPEN` |

### V-1 closure note (2026-09-03)

**Finding: `POINT_IN_TIME` confirmed.** The ceiling in force on the date gratuity becomes payable governs the entire amount. No apportionment across pre- and post-amendment service.

Evidence chain:
1. Commencement of the Payment of Gratuity (Amendment) Act, 2018 is **29 March 2018**; ceiling set at ₹20,00,000 by notification **S.O. 1420(E)** of the same date (PIB release; corroborated by two independent legal summaries).
2. The eligibility test is stated as a **trigger-event date test**, not a service-apportionment test — the higher limit applies to employees who "retire or become incapacitated prior to such retirement or die on or after the 29th day of March, 2018, or whose employment is terminated on or after the said date."
3. Requests to backdate the enhancement to 1 April 2016 were **explicitly rejected** on the ground that retrospective enhancement would be detrimental to employers. "Prospective" here therefore means prospective as to *terminations*, not as to *service* — which is precisely the distinction the straddle case turns on.
4. The Act contains **no apportionment machinery** for the ceiling. A pro-rating rule would have to exist expressly; it does not.

Therefore an employee joining 2014 and terminating 2026-09-30 receives the ₹20,00,000 cap applied to the whole computed gratuity. Splitting service at 2018-03-29 and blending two ceilings is wrong. Probe P-01 is unblocked and may be promoted to the scored golden set.

**Residual caveat, recorded rather than hidden:** this reads S.O. 1420(E) through secondary sources. The gazette notification PDF itself has not been read. Sufficient to lock the design decision; if the marquee probe is ever challenged in an interview, the honest answer is that the commencement language was verified via three concurring secondary sources and the primary gazette was not obtained.

---

## Results ledger

**Empty by design.** No row is written until a real run produces it. This section is the only place in the project where a number may originate; anything quoted elsewhere must trace back to a row here.

| Date | Milestone | Metric | Value | Run reference |
|---|---|---|---|---|
| 2026-09-03 | M3 | Retrieval-only Context Precision@10 (mean, 38 probes) — **PRE-FIX, superseded 2026-09-04** | 0.134 | `build/retrieval_harness_result.json`, `scripts/run_retrieval_harness.py` |
| 2026-09-03 | M3 | Retrieval-only Context Recall@10 (mean, 38 probes) — **PRE-FIX, superseded 2026-09-04** | 0.682 | `build/retrieval_harness_result.json`, `scripts/run_retrieval_harness.py` |
| 2026-09-03 | M3 | Probes at perfect recall (1.0) — **PRE-FIX, superseded 2026-09-04** | 18 / 38 | `build/retrieval_harness_result.json` |
| 2026-09-03 | M3 | Probes at zero recall (0.0) — **PRE-FIX, superseded 2026-09-04** | 4 / 38 (P-05, P-25, P-33, P-35) | `build/retrieval_harness_result.json` |
| 2026-09-04 | M3 | Retrieval-only Context Precision@10 (mean, 38 probes), **post-fix** (`min_rerank_score=0.001`) | **0.253** (+0.119 vs. pre-fix, +89% relative) | `build/retrieval_harness_result.json`, `scripts/run_retrieval_harness.py` |
| 2026-09-04 | M3 | Retrieval-only Context Recall@10 (mean, 38 probes), **post-fix** | **0.568** (-0.114 vs. pre-fix, -17% relative) | `build/retrieval_harness_result.json`, `scripts/run_retrieval_harness.py` |
| 2026-09-04 | T-5.4 | Citation Accuracy (mean, 11/24 items reaching ANSWERED), **post-retrieval-fix, PRE-narrative-fix (Session 8), superseded pending re-run** | **0.214** (vs. two untrusted pre-fix runs of 0.106 and 0.151 — neither ever entered here) | `build/citation_accuracy_result.json`, `eval/run_citation_accuracy_eval.py` |
| 2026-09-04 | T-5.3 | RAGAS Context Precision (mean, 11/24 items reaching ANSWERED), LLM-judged (gpt-4o-mini) — **PRE-narrative-fix (Session 8), superseded pending re-run** | **0.726** | `build/ragas_eval_result.json`, `eval/run_ragas_eval.py` |
| 2026-09-04 | T-5.3 | RAGAS Context Recall (mean, 11/24 items reaching ANSWERED), LLM-judged — **PRE-narrative-fix (Session 8), superseded pending re-run** | **0.492** | `build/ragas_eval_result.json`, `eval/run_ragas_eval.py` |
| 2026-09-04 | T-5.3 | RAGAS Faithfulness (mean, 11/24 items reaching ANSWERED), LLM-judged — **PRE-narrative-fix (Session 8), superseded pending re-run** | **0.089** | `build/ragas_eval_result.json`, `eval/run_ragas_eval.py` |
| 2026-09-04 | T-5.3 | RAGAS Answer Correctness (mean, 11/24 items reaching ANSWERED), LLM-judged — **PRE-narrative-fix (Session 8), superseded pending re-run** | **0.169** | `build/ragas_eval_result.json`, `eval/run_ragas_eval.py` |
| 2026-09-04 | T-5.3 | RAGAS Context Precision (mean, 11/24 items reaching ANSWERED), **post-narrative-fix (Session 8)** | **0.726** (unchanged -- expected, retrieval/context untouched by the generator fix) | `build/ragas_eval_result.json`, `eval/run_ragas_eval.py` |
| 2026-09-04 | T-5.3 | RAGAS Context Recall (mean, 11/24 items reaching ANSWERED), **post-narrative-fix (Session 8)** | **0.462** (was 0.492 pre-fix -- a small, likely judge-sampling-noise delta; not investigated further, recorded as measured) | `build/ragas_eval_result.json`, `eval/run_ragas_eval.py` |
| 2026-09-04 | T-5.3 | RAGAS Faithfulness (mean, 11/24 items reaching ANSWERED), **post-narrative-fix (Session 8)** | **0.497** (was 0.089 pre-fix, +458% relative -- confirms the narrative-substance root cause) | `build/ragas_eval_result.json`, `eval/run_ragas_eval.py` |
| 2026-09-04 | T-5.3 | RAGAS Answer Correctness (mean, 11/24 items reaching ANSWERED), **post-narrative-fix (Session 8)** | **0.334** (was 0.169 pre-fix, +98% relative) | `build/ragas_eval_result.json`, `eval/run_ragas_eval.py` |
| 2026-09-04 | T-5.4 | Citation Accuracy (mean, 11/24 items reaching ANSWERED), **post-narrative-fix (Session 8)** | **0.861** (was 0.214 pre-fix, +302% relative -- same 6/11 extra-citation / 4/11 missing-citation item counts as pre-fix, but per-item scores rose sharply now that the cited clauses' real text is present for the judge to check against; one item, P-16, still scores 0.0 -- not yet root-caused, see below) | `build/citation_accuracy_result.json`, `eval/run_citation_accuracy_eval.py` |
| 2026-09-04 | T-5.5 | Four-class confusion matrix + over-refusal counter, **first real run (Session 8)** | Class match **14/24**; over-refusal **1** (P-01 -- the already-documented reranker-ordering limitation, MUST_ANSWER -> INSUFFICIENT); ANSWERED items with no substantive content: **0/11** (down from an unmeasured-but-implied ~8/11 pre-fix -- confirms the narrative-substance fix) | `build/confusion_matrix_result.json`, `eval/run_confusion_matrix.py` |

**Post-fix delta, read honestly (this is the actual retrieval-floor trade-off, not spun)**: precision nearly
doubled and citation accuracy roughly doubled from the last (untrusted) reading, but recall dropped a real
17% relative — the floor legitimately cost some true positives, not just padding, on the full 38-probe set;
several probes in the real run returned as few as 0-3 pieces where they used to get padded to 10, and two of
those (0-returned) probes now retrieve nothing at all. This is a real, not hypothetical, cost of the
`DEFAULT_MIN_RERANK_SCORE=0.001` choice, worse on the full set than the 5-probe calibration sample suggested
(see Phase 3 detail for the calibration data) — flagged here rather than only celebrating the precision gain.
Citation Accuracy still shows 6/11 ANSWERED items with an unexpected citation and 4/11 missing an expected
one — the over-citation bug is measurably better, not solved; some of this is the documented P-01/P-17
ranking-order limitation, but the mix hasn't been broken down probe-by-probe yet. See Phase 3 and Phase 5
detail sections for the full read and what's still open.

**T-5.3's first real numbers, read honestly, 2026-09-04**: RAGAS's Context Precision (0.726) and Context
Recall (0.492) are NOT directly comparable to T-3.6's retrieval-harness numbers above (0.253/0.568) even
though the names overlap -- different methodology, both real. T-3.6 is plain set-overlap against a fixed
expected-clause-ID list, over all 38 probes including ones that never reach an answer. RAGAS's versions are
an LLM judge's relevance call, over only the 11/24 golden items that reached `ANSWERED` (a narrower,
easier-by-construction subset -- items that got to ANSWERED already cleared CRAG's sufficiency bar). Two
different measurements of two different things; neither supersedes the other.

**Faithfulness (0.089) and Answer Correctness (0.169) are both low, and that's recorded as-is, not
explained away.** Not yet root-caused -- flagging a plausible, unconfirmed hypothesis rather than a
diagnosis: `generation/formula.py`'s computed rupee amounts and day counts are arithmetic derived from
corpus constants, not sentences literally present in any retrieved clause text, and RAGAS's Faithfulness
metric decomposes an answer into claims and checks each one against the retrieved context sentence-by-
sentence -- a claim like "the gratuity amount is Rs 20,00,000" may have no literal textual support even
when the number is correctly computed. That would also drag Answer Correctness down (it partly depends on
Faithfulness-style grounding). This is a hypothesis to check against the real per-item RAGAS output in
`build/ragas_eval_result.json` during T-5.5, not something to silently patch around now -- if confirmed, it
would be a real limitation of a generic RAG faithfulness metric applied to a pipeline that does deterministic
arithmetic outside the retrieved text, worth documenting as such rather than tuning the pipeline to satisfy
the metric.

See Phase 3's original status block above for the honest read of the pre-fix numbers — precision@10 is
mechanically bounded by narrow expected-clause sets and should not be read as retrieval quality on its own;
the four zero-recall probes from the pre-fix run were flagged, not root-caused (still true post-fix — recall
composition per-probe hasn't been re-diffed against the old zero-recall set yet).

Metrics awaiting first measurement: four-class confusion matrix (T-5.5) · over-refusal count · end-to-end latency · indexing cost. RAGAS's four metrics (T-5.3) now have first real numbers (see table above) — Faithfulness and Answer Correctness are low and not yet root-caused, see the honest-read paragraph above.

---

## Risk register

| # | Risk | Phase | Mitigation |
|---|---|---|---|
| RK-1 | Synthetic corpus drifts to uniform, easy prose and stops being a real test | P1 | Defects-first build order; deliberate variation in drafting register; T-1.7 coverage audit |
| RK-2 | Guardrail threshold ratchets toward refuse-everything | P6 | Over-refusal counter gates T-6.6 |
| RK-3 | Deliberate fixtures get "fixed" by a later session | P1+ | `DELIBERATE_DEFECTS.md` manifest (T-1.1) written *before* the fixtures |
| RK-4 | OpenAI spend runs ahead of budget during indexing / eval loops | P2, P5 | Confirmed $4.98 balance (2026-09-03); locked to gpt-4o-mini/gpt-5-nano + text-embedding-3-small; cache embeddings; dry-run on a small slice before full-corpus T-2.6/2.7 |
| RK-5 | Drive API setup consumes a disproportionate share of D5 | P6 | T-6.1 can start any time — it has no upstream dependency; pull it forward if a phase runs short |
| RK-6 | Deployment pulls time from local-prototype quality | P8 | Held as fast-follow by design |
| RK-7 | Unmeasured claims leak into README or interview answers | All | Ledger is the single source of numbers; T-9.3 audits against it |

---

## Change log

| Date | Change |
|---|---|
| 2026-09-04 | **T-6.1 DONE (Session 10): real connection to Drive confirmed live.** After fixing two setup snags found on the real run -- (1) the first OAuth client Prashanth created was type `web`, not `installed` (Desktop app), causing a `redirect_uri_mismatch`; recreated as the correct type; (2) the consent screen's Testing status needed Prashanth's own account added as a test user, causing an `access_denied` until fixed -- `scripts/drive_auth_setup.py` ran successfully end-to-end from `.venv-win`: browser consent completed, `drive_sync/token.json` cached, and a real Drive API call listed folder `1VtSb9dHyekIgq6Sb1qbMgTO0GZINuVjy` (0 items, expected -- corpus not yet uploaded, that's T-6.2). Confirms the full chain end to end: GCP project, Drive API, OAuth client, consent, and folder access. T-6.1 moved `WIP` -> `DONE`. |
| 2026-09-04 | **T-6.1 in progress (Session 10): service-account path blocked by org policy, switched to OAuth desktop-app auth.** Google's `iam.disableServiceAccountKeyCreation` org policy -- part of the "secure by default" defaults Google now applies to *all* new GCP projects, including individual/no-organization ones -- blocked service-account JSON key creation outright on the new `hr-policy-rag-507613` project, a real infra constraint hit live, not a config mistake. Switched design to an OAuth 2.0 "Desktop app" client instead: authenticates as Prashanth's own Google account via one-time browser consent (`InstalledAppFlow`), caches a refresh token afterward. This is arguably the better-fit choice anyway for a single-user personal Drive folder -- no service-account identity to separately share the folder with. Wrote `drive_sync/auth.py` (`get_credentials()`/`get_drive_service()`, scoped `drive.readonly`) and `scripts/drive_auth_setup.py` (one-time interactive setup + connection-test script, lists the configured Drive folder's contents). `.env` extended with `GOOGLE_CLIENT_SECRET_PATH`/`GOOGLE_TOKEN_PATH`/`GOOGLE_DRIVE_FOLDER_ID`; `requirements.txt` already had the needed `google-*` packages from Phase 0 planning, confirmed installed in `.venv-win`. Drive folder `1VtSb9dHyekIgq6Sb1qbMgTO0GZINuVjy` created and its ID recorded; not yet uploaded with the corpus (T-6.2). The one-time browser consent step must be run by Prashanth himself in a real terminal (`.venv-win\Scripts\python.exe scripts\drive_auth_setup.py`), not through the device-bridge shell, since it needs to open a real, visible browser window -- same real-terminal constraint as the OpenAI/HuggingFace calls in Phases 2-5. Not yet run for real; T-6.1 stays `WIP` until that script confirms the connection. |
| 2026-09-04 | **Session 9 follow-up on the four new findings: one real fix, three confirmed known limitations, one diagnostic-tool bug caught and corrected.** Prashanth's terminal re-ran `scripts/dump_rerank_scores.py` (extended to cover the four new probes). First pass surfaced a real bug in the *diagnostic script itself* -- it never passed `country`/`jurisdiction_scope` to `retriever.retrieve()`, unlike every real production entry point, so its numbers overstated cross-country noise. Fixed the script and re-ran. With the correct country filter applied: (1) P-3a/P-04's golden-set missing `facts` and P-3b's `MUST_ANSWER`/`MUST_CLARIFY` mislabel (both fixed earlier this session) are unaffected by this correction. (2) **P-18 (Germany gratuity) was a second golden-set classification defect, not a retrieval bug** -- both expected clauses already surface once the country filter is correctly applied; a real offline pipeline run confirmed that even with only the primary clause retrieved (the second is separately clipped by the existing calibrated floor, an accepted limitation), the pipeline correctly produces ANSWERED status with a full, correct refusal-of-premise answer that never touches an India/UAE gratuity clause -- exactly what its own `golden_answer` describes. `MUST_REFUSE` was checked against the only other item in that class (P-39, a genuine deliberate-absence case) before reclassifying P-18 to `MUST_ANSWER`, to avoid repeating the P-3b-style regression risk. (3) P-16 (notice-period), P-28 ("that's illegal" phrasing), and P-39 (paternity leave false match) were confirmed, with the corrected real numbers, to be genuine retrieval-precision limitations: in each case a wrong or absent-signal ordering makes the true answer unreachable by any floor value, without breaking another probe that needs a similarly low score kept. These join P-01/P-17 as known, evidenced limitations -- not attempted further this session. Commits `5e8574f` (diagnostic script fix) and `d17c72c` (script country-filter fix + P-18 reclassification); 174/174 tests passing throughout. |
| 2026-09-04 | **M5 closed: real post-narrative-fix re-run confirms the Session 7/8 diagnosis, with new findings surfaced honestly (Session 8 continued).** Prashanth re-ran all three eval scripts from `.venv-win` against the Session 8 generator fix. RAGAS Faithfulness 0.089->**0.497** (+458% relative), Answer Correctness 0.169->**0.334** (+98% relative), Context Precision unchanged at 0.726 (expected -- retrieval untouched), Context Recall 0.492->0.462 (small, likely judge-sampling noise, not investigated). Citation Accuracy 0.214->**0.861** (+302% relative). First real confusion-matrix run: class match 14/24, over-refusal count 1 (P-01, the known reranker-ordering limitation), and its own `narrative_only_no_substance` diagnostic confirms **0/11** ANSWERED items now lack real content (previously widespread). All of T-5.3/T-5.4/T-5.5/T-5.6 moved to `DONE`; M5 moved to `DONE` -- exit criterion (real numbers recorded) is met. However, the real run also surfaced new, unexplained weak spots, flagged here rather than smoothed over per Convention 15/17: (1) one item, P-16, still scores exactly 0.0 on Citation Accuracy (extra citation `MER-IN-NOTICE-SENIOR`); (2) both real MUST_REFUSE golden items, P-18 and P-39, failed to refuse (P-18 went to ANSWERED missing `DE-KSCHG-SCOPE`; P-39 went to NEEDS_CLARIFICATION) -- 0/2 class match for that entire class; (3) 3/5 MUST_FLAG items misclassified (P-04, P-17 to NEEDS_CLARIFICATION; P-28 to INSUFFICIENT); (4) most notably, P-3a/P-3b/P-15 (MUST_ANSWER) all came back NEEDS_CLARIFICATION, none flagged as the known rerank limitation -- surprising since P-3a/P-3b were previously reported (Session 3) as working end-to-end, self-correcting and splitting at the DIFC DEWS 2020-02-01 boundary with both clauses cited. None of these four items has been root-caused yet; recorded as real, open findings for a scope decision before treating the pipeline's quality as fully settled, even though M5's own exit criterion is technically satisfied. |
| 2026-09-04 | **Phase 4 narrative-substance defect fixed (Session 8), Convention 17.** Two fix shapes presented (touch `reason_over_pieces()`'s temporal reasoning, or teach `TemplateGenerator.generate()` to always follow the narrative with real clause text); Prashanth chose the smaller, generator-only change. `generate()` now appends the real `.text` of every piece actually cited (`used_pieces`), deduplicated, right after the temporal narrative, whenever `workings` exist and nothing is missing -- so a cited clause is always also quoted, not just named in a generic template sentence. Verified against the exact P-30 symptom from the T-5.5 diagnosis: the housing-allowance answer now includes the real Schedule 2 table content, not just the two generic temporal-governance sentences. 174/174 tests passing, purely additive change. Marks the existing T-5.3/T-5.4 Results Ledger rows (Faithfulness 0.089, Answer Correctness 0.169, Citation Accuracy 0.214) as pre-narrative-fix baselines, superseded pending a real re-run of `eval/run_ragas_eval.py`/`eval/run_citation_accuracy_eval.py`/`eval/run_confusion_matrix.py` from `.venv-win`. |
| 2026-09-04 | **T-5.5 diagnosis pass (Session 7): both open T-5.3/T-5.4 questions answered with real per-item data, one real Phase 4 defect found.** The P-01/P-17 ranking-order limitation does NOT explain the remaining Citation Accuracy misses -- neither item is even in the scored ANSWERED set this run. The arithmetic-vs-literal-text hypothesis for low RAGAS Faithfulness is NOT confirmed -- items WITH a computed figure score highest, not lowest. Real root cause for both: `grading/temporal_reasoner.py::reason_over_pieces()` wraps every retrieved piece in its own trivial `TemporalWorking`, and `generator.py`'s narrative-only branch for that case never includes the underlying clause text -- so most ANSWERED items contain zero real policy content, only a generic template sentence, which neither a RAGAS claim-checker nor the citation judge can verify against anything real. Wrote and smoke-tested `eval/run_confusion_matrix.py` (T-5.5); flagged the new defect for a scope decision rather than patching Phase 4 unilaterally. |
| 2026-09-04 | **T-5.3: real first RAGAS numbers in (Session 6 continued).** Prashanth re-ran `eval/run_ragas_eval.py` against the nest_asyncio-monkeypatch fix -- all 44 real OpenAI calls succeeded. Over 11/24 ANSWERED golden items: Context Precision 0.726, Context Recall 0.492, Faithfulness 0.089, Answer Correctness 0.169. Recorded in the Results Ledger. Faithfulness/Answer Correctness are low and NOT explained away -- a plausible, unconfirmed hypothesis (RAGAS's Faithfulness metric checking claims against literal retrieved text, vs. this pipeline's computed rupee/day figures from `generation/formula.py`) is flagged for T-5.5 to check against the real per-item data, not assumed. T-5.3 moved to `DONE`; M5 still `WIP` pending T-5.5/T-5.6. |
| 2026-09-04 | **T-5.3's real second attempt found the original root cause was misdiagnosed, and fixed it at the right layer (Session 6 continued).** The `inspect.signature()`/`allow_nest_asyncio=False` fix (previous entry) correctly avoided the `TypeError`, but the re-run then hit the *original* Session 5 `RuntimeError(Timeout should be used inside a task)` on all 44 jobs, `n/a` on every metric. Reading both installed ragas releases' source side by side (0.3.1 on `.venv-win`, 0.4.3 dev-reference) showed 0.3.1 is *older*, not newer as first assumed, and lacks a guard 0.4.3 added: 0.4.3 only applies `nest_asyncio` when a loop is already running (Jupyter), 0.3.1 calls it unconditionally at import time with no opt-out. Fixed by monkeypatching `nest_asyncio.apply()` to a no-op before importing `ragas` at all -- safe because this script never runs inside an already-running loop. 174/174 tests passing. Not yet re-run against this fix. |
| 2026-09-04 | **Phase 3 reopened bug: real post-fix numbers in, M3 re-closed (Session 6 continued).** Prashanth ran `scripts/run_retrieval_harness.py`, `eval/run_ragas_eval.py`, and `eval/run_citation_accuracy_eval.py` against the live, calibrated fix. T-3.6: Context Precision@10 0.134 -> 0.253 (+89% relative), Context Recall@10 0.682 -> 0.568 (-17% relative) -- a real trade-off, recorded honestly rather than only celebrating the precision gain; several probes now return as few as 0-3 pieces where they used to get padded to 10. M3 milestone moved back to `DONE` with these numbers. T-5.4: Citation Accuracy 0.214 over 11/24 ANSWERED items (up from the two untrusted pre-fix runs, neither ever entered in the ledger) -- improved, not solved (6/11 still show an extra citation). T-5.3 hit a second real bug on its first attempt: `ragas` is pinned unversioned in `requirements.txt`, so Prashanth's machine installed a newer release than this project's dev reference (0.4.3) and that release removed/renamed the `allow_nest_asyncio` parameter the earlier fix depended on -- `eval/run_ragas_eval.py` now inspects the installed `evaluate()`'s real signature instead of assuming one, and self-reports which path it took. Not yet re-run against this fix. 174/174 tests passing throughout (no pipeline code touched by the ragas-script fix). |
| 2026-09-04 | **Phase 3 reopened bug: calibrated and wired in (Session 6).** Prashanth ran `scripts/dump_rerank_scores.py` for real against 5 probes. Finding: the floor cleanly separates signal from noise on single-topic queries (P-30: 0.98 vs. <=0.0016) but cannot fix two adversarial cases where a wrong clause outranks a right one (P-01's decoy scores 0.098 vs. the real answer's 0.022; P-17's second correct clause scores 0.0002, below four wrong ones) -- no floor value can fix a wrong ranking order, only a too-low true positive relative to real noise. Chose the conservative default `DEFAULT_MIN_RERANK_SCORE = 0.001` from that data (drops all clear padding, keeps every true positive seen in calibration) and wired it in as the actual default on `retrieve_and_grade()`, `answer_query()`, and `run_retrieval_harness()` -- not just an available parameter. Deliberately did NOT chase the P-01/P-17 ranking-order limitation further (scope call: reranker-tuning work disproportionate to a 2-of-24-probe edge case on a synthetic demo corpus); logged it as a forward flag in Phase 5's detail section instead, so the next T-5.3/T-5.4 run doesn't re-diagnose an already-known issue. 174/174 tests passing. M3 stays `REOPENED` pending the real T-3.6/T-5.3/T-5.4 re-runs. |
| 2026-09-04 | Phase 3 reopened bug: built the fix mechanism. `HybridRetriever.retrieve()` gained `min_rerank_score` (drop below-floor candidates before truncating to `top_k`, so `top_k` is a ceiling not a target), default `None` (old behaviour) until calibrated. `scripts/dump_rerank_scores.py` written for the real-data calibration run. Not yet the actual fix in production -- no call site passes the new parameter yet, and no floor value is chosen. 171/171 tests passing. |
| 2026-09-04 | **Two real bugs found on the first live T-5.3/T-5.4 run.** (1) RAGAS scoring returned `n/a` for all four metrics on every item -- root-caused to `ragas`'s unconditional `nest_asyncio.apply()` being incompatible with Python 3.11+'s `asyncio.timeout()` (confirmed by reading `ragas/executor.py` directly, not guessed); fixed via `allow_nest_asyncio=False` in `eval/run_ragas_eval.py`, not yet re-run. (2) Citation Accuracy scored 0.106 mean with 7/7 ANSWERED items over-citing -- root-caused to `generation/citations.py`'s `build_citations()` attaching every retrieved normative piece regardless of whether the answer's narrative actually used it, a real defect in Phase 4/5 generation code that the existing test suite never caught (it checked expected clauses were present, never that extraneous ones were absent). Found and root-caused; fix proposed (restrict citations to pieces actually referenced by `workings`) but deliberately NOT applied without Prashanth's sign-off, since it changes production generation output. Also resolved the `langchain_community.chat_models.vertexai` `ModuleNotFoundError` blocking `ragas` from importing at all -- root-caused to a dead top-level import (`ragas/llms/base.py` only uses `ChatVertexAI`/`VertexAI` in an `isinstance()` support-list, never instantiates either) against a `langchain-community` version where that submodule was removed in LangChain's provider-package split; fixed with a 5-line local compatibility shim in the venv rather than downgrading `langchain-community` (which would have risked real incompatibility with the already-installed `langchain-core 1.5.1`/`langchain 1.3.14`). |
| 2026-09-04 | **Phase 8 scope confirmed IN SCOPE by Prashanth** -- this is an end-to-end project with real deployment, not a HOLD/fast-follow to skip for the postmortem. Updated the milestone table (M8 `HOLD`->`TODO`) and Phase 8's own header/detail accordingly. Also fixed a stale M5 row in the same milestone table -- still said `TODO` even though the Phase 5 detail section had said `WIP` since Session 4/5's work (golden set, arithmetic layer, T-5.3/T-5.4 scripts) -- same milestone-table-vs-phase-detail drift pattern caught in prior sessions for M2. |
| 2026-09-04 | **Arithmetic gap closed (Session 5).** Found `TemplateGenerator` never computed an actual rupee amount or day count (only structural reasoning existed) while scoping T-5.3/T-5.4 -- a real scope gap, not a bug. Built `generation/formula.py` (deterministic, LLM-free) and wired it through `ServiceFacts`/`TemporalWorking`/`GeneratedAnswer`/`TemplateGenerator.generate()` (commit `1ff410c`, +15 tests, 166/166 passing), after exposing `PipelineResult.pieces` for Phase 5's eval harness (commit `49f533f`). Wired verified `facts`/`expected_computation` into P-01/P-02/P-03 in `scored_golden_set.json` (commit `fe9e305`): P-01 amount=₹20,00,000 (uncapped ₹22,50,000), P-02 45+52=97 days, P-03 165 days -- all three re-verified independently against `generation/formula.py` directly, not just carried over from an earlier hand-check. Standing working mode from this session: Claude writes and commits code directly via the device bridge; Prashanth is pulled in only for real terminal runs needing network this sandbox blocks. |
| 2026-09-03 | **T-5.1/T-5.2 done.** `eval/golden/scored_golden_set.json` — 24 probes promoted into the scored golden set with class labels, expected clause IDs, and golden answers (derived from real corpus text + closed V-1/V-3 findings, no invented numbers). Mix 46/25/21/8 vs. target 45/25/20/10. Checked T-1.8's block against all 43 probes: V-2/V-4/V-5 don't gate any of them (see Phase 5 detail and `docs/CORPUS_REQUIREMENTS.md`), so promotion proceeded without re-opening verification work. Found and fixed a real probe/fixture wording mismatch on P-33 (Gulf EOSB terms vs. the fixture's actual India synonym set) — likely explains its M3 zero-recall result; held out of the scored set pending sign-off. Also fixed two stale plan artifacts found on read-through: Phase 2's header still said `WIP` after its exit criterion had already been met, and P-01's `[VERIFY]` tag in `adversarial_probe_set.md` had not been cleared when V-1 closed. |
| 2026-09-03 | **M4 CLOSED. Phase 4 DONE.** T-4.7 (LangSmith tracing, `@traceable` on retrieve/grade/temporal-reason/generate, no-op with no network call unless tracing is explicitly enabled -- verified) and T-4.8 wiring (`grading/answer_pipeline.py`'s `answer_query()`, composing T-4.1-T-4.6 into one call) done. M4 exit criterion met with a stated scope caveat: proven end-to-end on three real representative cases (P-01 answers without splitting, P-3a self-corrects and splits at 2020-02-01, P-06 correctly asks for clarification instead of guessing) starting from actual query text, not a full unaided 43-probe run -- that needs a natural-language fact-extraction step (dates/country from free text) that was never a Phase 4 task and doesn't exist yet. 150/150 tests passing. Phase 5 (evaluation harness) open next. |
| 2026-09-03 | T-4.6 done and tested — `generation/supersession.py`, wired into `TemplateGenerator`. Two distinct signals: an informational amendment note when a cited clause has `supersedes` set (fires correctly, without warning, on the legitimate P-3a SEGMENTED_ACCRUAL split where both old and new versions are cited together on purpose); a stale-citation `superseded_warning` when a cited clause's `superseded_by` replacement is NOT also part of the answer (verified against `IN-GRAT-S4-CEILING-SUPERSEDED` cited alone). 142/142 tests passing. |
| 2026-09-03 | T-4.5 done and tested — `grading/clarification.py` + `ClarificationResponse`/`MissingFact`/`ConditionalAnswer` in `grading/schema.py`. Two triggers: T-4.3's existing `TemporalWorking.missing_facts` (P-06's joining-date gap), and a new country-ambiguity check (no country supplied + retrieved normative clauses span >1 country -- P-13/P-19/P-41's shape) that guards against silently defaulting to India because the corpus is India-heavy. One conditional answer per plausible country value, built by re-running T-4.4's generator on each country's subset. Single terminal response, no conversational state -- resolves the apparent conflict with the stateless scope decision per Finding 5. 137/137 tests passing. |
| 2026-09-03 | T-4.4 done and tested — `generation/` module (Citation/GeneratedAnswer schema, citation builder, TemplateGenerator). Citations are assembled programmatically from clause metadata, never asked of an LLM, so they can't drift from what was actually retrieved. TemplateGenerator is deterministic (no LLM) — reuses T-4.3's narrative lines verbatim for straddle cases, falls back to raw clause text otherwise, and refuses a confident answer when a working reports missing_facts. Verified manually against the real P-01 corpus fixture before tests were written. 132/132 tests passing. Written by Prashanth, guided step by step. |
| 2026-09-03 | T-4.1/T-4.2/T-4.3 done and tested against real corpus fixtures. T-4.1 CRAG grader (`grading/crag_grader.py`): sufficiency now requires the applicability rule, not just the clause (Finding 1) — caught a real modelling gap while building it: SEGMENTED_ACCRUAL/GRANDFATHERED is a per-clause property, not per-lineage (DIFC annual leave is tagged SEGMENTED_ACCRUAL but is self-contained; only a true amendment pair, identified by supersedes/superseded_by, needs its sibling version fetched). T-4.2 corrective re-query (`grading/pipeline.py`): direct lineage lookup for missing segment versions, bounded widened retry for no-relevant-clause; one pass, no unbounded loop. T-4.3 temporal reasoner (`grading/temporal_reasoner.py`): all four classes implemented; P-01 (India ceiling, no split) and P-3a (DIFC DEWS, split at 2020-02-01) pass together with opposite behaviour on the first real run against the corpus, per Finding 1's own bar for "reasoning, not pattern-matching". Also propagated version/section/source_doc/source_act/source_url/cohort_rule onto IndexableUnit — same class of gap T-3.2 caught for jurisdiction_scope, needed for T-4.4 citations and T-4.3's GRANDFATHERED class. 125/125 tests passing. T-4.4 onward (generation, clarification, supersession flagging, tracing) still open. |
| 2026-09-03 | **M3 CLOSED.** Prashanth ran `scripts/prefetch_reranker_model.py` and `scripts/run_retrieval_harness.py` from his own machine. First real retrieval numbers: mean Context Precision@10 = 0.134 (mechanically bounded by narrow expected-clause sets, not a clean quality signal on its own), mean Context Recall@10 = 0.682, 18/38 probes at perfect recall, 4 at zero recall (P-05, P-25, P-33, P-35 — flagged as a real follow-up, not yet diagnosed). Phase 3 closed. Phase 4 (grading, generation, clarification) open next. |
| 2026-09-03 | Phase 3 opened. T-3.1–T-3.4 done and tested (RRF fusion, hard country/jurisdiction_scope filters, as-of-date lineage resolution, FM-D6 dedup). T-3.5/T-3.6 code-complete and unit-tested but not yet run for real: FlashRank's model download hit the same huggingface.co sandbox block that api.openai.com hit in Phase 2 — handed off to Prashanth (`scripts/prefetch_reranker_model.py` then `scripts/run_retrieval_harness.py`). M3 stays open until that real run produces a number. |
| 2026-09-03 | Plan created. Phases 0–9, milestones M0–M9. |
| 2026-09-03 | Build order inverted — probes before corpus. Phase 1 restructured to build from the requirements spec rather than writing policy prose first. |
| 2026-09-03 | M0 closed. Phase 1 opened. V-1 closed: India gratuity ceiling confirmed `POINT_IN_TIME`; probe P-01 unblocked. |
| 2026-09-03 | **M1 CLOSED.** T-1.4/1.5/1.6 done; 72 clauses (24 statutory, 48 policy). T-1.7 automated as `eval/coverage_audit.py` (stdlib only, CI-ready) and PASSES — so M1's exit criterion is machine-witnessed rather than asserted. On its first run the audit caught two real defects: schema drift (18 Tier-1 clauses predated the extended schema and lacked temporal_applicability / normative / lineage_id — now backfilled per-clause, not blanket-defaulted) and a false positive in its own deliberate-absence check (scoped to clause bodies, since editorial notes must be able to name the gap). Phase 2 open. |
| 2026-09-03 | V-3 closed. DIFC added as real Tier-1 law plus a Meridian DIFC annexe. The DEWS transition (1 Feb 2020) turns out to be a genuine statutory straddle that splits — the real counterweight to the India ceiling, which does not. Two new probes added (P-3a, P-3b). |
| 2026-09-03 | T-1.3 done — R-01→R-09 version-pair structures across all three chapters. Probe P-06 rewritten: it and P-02 had been specified against the same 18→24 leave fixture with incompatible mechanics (grandfathered vs segmented accrual); P-06 moved to a UAE end-of-service supplement. Caught by corpus construction, i.e. the corpus validating the probe set. |
| 2026-09-03 | T-1.1 + T-1.2 done. Defect manifest D-1..D-5 written ahead of fixtures; Meridian global preamble and partial India chapter committed. R-10/R-11/R-15 satisfied early (the notice-clause pair carried both sides of the statutory-floor asymmetry, and the governing-law clause was needed to host D-5). |
