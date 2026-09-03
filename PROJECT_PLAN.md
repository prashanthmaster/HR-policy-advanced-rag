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

**Calendar note.** Phases are numbered by working day (D1–D7) against the Slot 4 allocation in `AI_Engineer_14Day_Schedule.pdf`. That file lives in the `Career_Transition` folder, which is not connected to this session — day-to-calendar mapping is therefore indicative, not authoritative. Connect the folder and it can be reconciled properly.

---

## Milestone summary

| # | Milestone | Exit criterion (demonstrable) | Day | Status |
|---|---|---|---|---|
| **M0** | Design locked, corpus grounded | Corpus decision closed; Tier-1 real statutory corpus committed; failure register + probe set + corpus spec committed | D1 | `DONE` |
| **M1** | Corpus complete | Every requirement R-01→R-25 has a corpus artifact; every probe has something to bite on; defect manifest exists | D1–D2 | `DONE` |
| **M2** | Indexed | Corpus fully indexed under the extended schema; proviso-boundary and metadata tests pass | D2–D3 | `DONE` |
| **M3** | Retrieval measured | Retrieval-only Context Precision + Recall **measured** against the probe set and recorded in the ledger | D3 | `DONE` |
| **M4** | End-to-end answers | Pipeline answers the probe set with citations; clarification contract returns structured output on `MUST_CLARIFY` items | D4 | `DONE` (composition proven on representative real cases -- see caveat in Phase 4 detail) |
| **M5** | Baseline scored | All 5 metrics + the four-class confusion matrix run on the golden set; **first real numbers** recorded | D4–D5 | `TODO` |
| **M6** | Freshness demoable | A document edited in Drive is picked up, re-indexed incrementally, and the answer changes correctly on camera | D5–D6 | `TODO` |
| **M7** | Regression-gated | CI runs the eval on push and fails the build on regression from recorded baseline | D6 | `TODO` |
| **M8** | Deployed | Public Cloud Run URL answers a query end-to-end; LangSmith trace inspectable | D7 | `HOLD` |
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

---

### Phase 5 — Evaluation harness · `WIP` · D4–D5

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-5.1 | Promote 20–30 probes into the scored golden set; fill golden answers + expected source clauses | M4, T-1.8 | `DONE` |
| T-5.2 | Label every item `MUST_ANSWER` / `MUST_REFUSE` / `MUST_CLARIFY` / `MUST_FLAG`; hold the ~45/25/20/10 mix | T-5.1 | `DONE` |
| T-5.3 | RAGAS: Context Precision, Context Recall, Faithfulness, Answer Correctness | T-5.2 | `TODO` |
| T-5.4 | Custom Citation Accuracy (LLM-as-judge, FinGuard G-Eval pattern) | T-5.3 | `TODO` |
| T-5.5 | Four-class confusion matrix + **over-refusal counter as a first-class defect** (Finding 3) | T-5.2 | `TODO` |
| T-5.6 | Baseline run; record every number in the ledger | T-5.4, T-5.5 | `TODO` |

**Exit criterion (M5):** ledger populated with measured baselines. Until this milestone, the project has **no** numbers and none may be quoted anywhere.

**T-5.1/T-5.2 done 2026-09-03**: `eval/golden/scored_golden_set.json`, 24 items drawn from the 43-probe adversarial set, each carrying a class label, expected source clause IDs, and a golden answer derived from real corpus clause text (plus the closed V-1/V-3 verification findings) — no invented figures. Actual mix 46/25/21/8 (target 45/25/20/10). P-01's stale `[VERIFY]` tag removed in `adversarial_probe_set.md` (V-1 closed). **Real bug caught while curating**: P-33's probe wording used Gulf EOSB terminology that matches none of its fixture's actual four synonym names (long service award / loyalty payment / continuity recognition / service milestone grant) — corrected in `adversarial_probe_set.md`; this is the likely real explanation for P-33's zero-recall result in the M3 run (probe/fixture mismatch, not a demonstrated retrieval failure). P-33 held OUT of the scored set this round pending confirmation of the corrected wording. T-5.3–T-5.6 (RAGAS, Citation Accuracy, confusion matrix, baseline run) open next — the LLM-as-judge metrics need a by-hand script run outside this sandbox, same pattern as `build_vector_index.py`/`prefetch_reranker_model.py`.

**Blocked by T-1.8:** an item still carrying `[VERIFY]` cannot be promoted into the scored set. **Checked 3 Sep 2026 (Session 4):** none of the 43 probes actually require a golden answer keyed to V-2/V-4/V-5 — the UAE 1980→2021 transition (V-2) was never built as a corpus fixture (DIFC/DEWS took the real-straddle-case role instead, as V-3, already closed), and V-4/V-5 (Indian state variation, Labour Codes commencement) are already handled by an explicit "national baseline, Codes not yet in force" scoping note inside `corpus/tier1_law/india/india_law.md` itself. T-1.8 therefore does not block T-5.1 in practice; V-2/V-4/V-5 stay open and untouched, tracked as future corpus/verification work, not as a Phase 5 gate.

---

### Phase 6 — Freshness & guardrail · `TODO` · D5–D6

The differentiator. Everything before this is table stakes.

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-6.1 | GCP project + Drive API enablement + credentials (from scratch — none exist yet) | — | `TODO` |
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

### Phase 8 — Deployment · `HOLD` (fast-follow) · D7

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-8.1 | Dockerize | M6 | `TODO` |
| T-8.2 | Qdrant Cloud; migrate index off local | T-8.1 | `TODO` |
| T-8.3 | Deploy to Cloud Run | T-8.2 | `TODO` |
| T-8.4 | FastAPI endpoint + minimal query UI | T-8.3 | `TODO` |
| T-8.5 | Smoke test against the deployed URL | T-8.4 | `TODO` |

**Exit criterion (M8):** public URL answers end-to-end; LangSmith trace inspectable for that answer.

Explicitly a fast-follow. Local prototype quality outranks deployment speed.

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
| 2026-09-03 | M3 | Retrieval-only Context Precision@10 (mean, 38 probes) | 0.134 | `build/retrieval_harness_result.json`, `scripts/run_retrieval_harness.py` |
| 2026-09-03 | M3 | Retrieval-only Context Recall@10 (mean, 38 probes) | 0.682 | `build/retrieval_harness_result.json`, `scripts/run_retrieval_harness.py` |
| 2026-09-03 | M3 | Probes at perfect recall (1.0) | 18 / 38 | `build/retrieval_harness_result.json` |
| 2026-09-03 | M3 | Probes at zero recall (0.0) | 4 / 38 (P-05, P-25, P-33, P-35) | `build/retrieval_harness_result.json` |

See Phase 3's status block above for the honest read of these numbers — precision@10 is mechanically bounded
by narrow expected-clause sets and should not be read as retrieval quality on its own; the four zero-recall
probes are flagged, not yet root-caused.

Metrics awaiting first measurement: Faithfulness · Answer Correctness · Citation Accuracy · four-class confusion matrix · over-refusal count · end-to-end latency · indexing cost.

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
