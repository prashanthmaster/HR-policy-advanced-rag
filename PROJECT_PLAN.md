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
| **M1** | Corpus complete | Every requirement R-01→R-25 has a corpus artifact; every probe has something to bite on; defect manifest exists | D1–D2 | `WIP` |
| **M2** | Indexed | Corpus fully indexed under the extended schema; proviso-boundary and metadata tests pass | D2–D3 | `TODO` |
| **M3** | Retrieval measured | Retrieval-only Context Precision + Recall **measured** against the probe set and recorded in the ledger | D3 | `TODO` |
| **M4** | End-to-end answers | Pipeline answers the probe set with citations; clarification contract returns structured output on `MUST_CLARIFY` items | D4 | `TODO` |
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

### Phase 1 — Corpus construction · `WIP` · D1–D2

Builds the Tier-2 synthetic layer (**Meridian Global Services**, fictional, banner-labelled) to satisfy the requirements spec. Build order is from `CORPUS_REQUIREMENTS.md` §3 and is not arbitrary: things that *look like mistakes* are written first, with their intent recorded, so they don't get tidied away later.

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-1.1 | `docs/DELIBERATE_DEFECTS.md` manifest — non-compliant clause, decoy illustration, intentional gaps | — | `TODO` |
| T-1.2 | Deliberate-defect clauses: R-11 (policy below statutory floor), R-20 (₹50,000 decoy illustration), R-25 (paternity-leave gap), R-23 (low-salience clause) | T-1.1 | `TODO` |
| T-1.3 | Version-pair structures: R-01→R-09 (segmented accrual, grandfathered, future-dated, retroactive, silent + partial supersession, sunset, renumbering, vague effective date) | T-1.2 | `TODO` |
| T-1.4 | Conflict structures: R-10→R-15 (above/below floor, free-zone annexe, near-identical cross-country, divergent definitions, governing-law clause) | T-1.3 | `TODO` |
| T-1.5 | Retrieval-mechanic structures: R-16→R-24 (slab table, proviso, cross-reference, synonym spread, near-duplicate pair, scattered operands, false-premise bait) | T-1.4 | `TODO` |
| T-1.6 | Ordinary connective policy prose — **written last**, deliberately: distractor mass is part of the test environment | T-1.5 | `TODO` |
| T-1.7 | Coverage audit: assert every R-requirement and every probe maps to a real corpus artifact | T-1.6 | `TODO` |
| T-1.8 | Work the `[VERIFY]` register down (see §Verification Register) | — | `TODO` |

**Exit criterion (M1):** T-1.7 audit passes — no probe is unanswerable for want of a document, and no requirement is unimplemented.

**Risk:** an LLM-written policy manual drifts toward uniform, plausible, *easy* prose — which would quietly defeat the whole point. Mitigation is T-1.6's ordering and a deliberate variation in register, clause density, and drafting quality across chapters.

---

### Phase 2 — Ingestion & indexing · `TODO` · D2–D3

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-2.1 | Parser: metadata blocks → structured chunk records | M1 | `TODO` |
| T-2.2 | Extended chunk schema: `temporal_applicability`, `revision_date`, `indexed_at`, `normative`, `lineage_id`, `supersedes`/`superseded_by`, `cohort_rule`, `jurisdiction_scope` | T-2.1 | `TODO` |
| T-2.3 | Clause-aware chunker — **hard rule: a proviso is never split from its clause** (FM-D2) | T-2.1 | `TODO` |
| T-2.4 | Table extraction → row-serialised text, separate chunk stream (per the no-vision decision) | T-2.3 | `TODO` |
| T-2.5 | Change-kind classifier: `NO_OP` / `EDITORIAL` / `SUBSTANTIVE` / `ADDITION` / `SUNSET` | T-2.2 | `TODO` |
| T-2.6 | BM25 index build | T-2.3 | `TODO` |
| T-2.7 | Vector index build — Qdrant local, `text-embedding-3` | T-2.3 | `TODO` |
| T-2.8 | Unit tests: proviso integrity, three-clock separation, lineage linkage, normative flagging | T-2.5 | `TODO` |

**Exit criterion (M2):** full corpus indexed; T-2.8 green.

**Gate:** T-2.7 is the first step that spends OpenAI credit. Confirm the key and its balance before running it.

---

### Phase 3 — Retrieval core · `TODO` · D3

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-3.1 | Reciprocal Rank Fusion over BM25 + vector | M2 | `TODO` |
| T-3.2 | Hard metadata filters: country, `jurisdiction_scope` (FM-B6 — soft embedding preference is not sufficient) | T-3.1 | `TODO` |
| T-3.3 | As-of-date filter on `effective_date`, overridable, default today (Finding 2) | T-3.2 | `TODO` |
| T-3.4 | Lineage dedup + top-k diversity before rerank (FM-D6) | T-3.3 | `TODO` |
| T-3.5 | FlashRank rerank; record the cutoff and the reason for it | T-3.4 | `TODO` |
| T-3.6 | Retrieval-only harness: Context Precision + Recall over the probe set | T-3.5 | `TODO` |

**Exit criterion (M3):** T-3.6 produces real numbers, recorded in the ledger. This is the first entry in §Results.

**Why retrieval is measured before generation exists:** a generation bug and a retrieval bug produce the same symptom — a wrong answer. Measuring retrieval alone first means the later end-to-end numbers are attributable. This is also the honest answer to "how do you know the reranker earns its place?"

---

### Phase 4 — Grading, generation & clarification · `TODO` · D4

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-4.1 | CRAG grading node — sufficiency test **includes the applicability rule**, not just the clause (Finding 1) | M3 | `TODO` |
| T-4.2 | Corrective re-query path on insufficient context | T-4.1 | `TODO` |
| T-4.3 | Temporal reasoning: apply `temporal_applicability` class; show the working on straddle cases | T-4.1 | `TODO` |
| T-4.4 | Generation, context-only, with clause-level citations (doc, section, version, effective date) | T-4.2 | `TODO` |
| T-4.5 | Stateless clarification contract: `NEEDS_CLARIFICATION` + `missing_facts[]` + `conditional_answers[]` (Finding 5) | T-4.4 | `TODO` |
| T-4.6 | Supersession flagging in answers (FM-E6) | T-4.4 | `TODO` |
| T-4.7 | LangSmith tracing on retrieval / grading / generation | T-4.4 | `TODO` |

**Exit criterion (M4):** the probe set runs end-to-end; `MUST_CLARIFY` probes return structured clarification rather than a guess or a flat refusal.

---

### Phase 5 — Evaluation harness · `TODO` · D4–D5

| ID | Task | Depends on | Status |
|---|---|---|---|
| T-5.1 | Promote 20–30 probes into the scored golden set; fill golden answers + expected source clauses | M4, T-1.8 | `TODO` |
| T-5.2 | Label every item `MUST_ANSWER` / `MUST_REFUSE` / `MUST_CLARIFY` / `MUST_FLAG`; hold the ~45/25/20/10 mix | T-5.1 | `TODO` |
| T-5.3 | RAGAS: Context Precision, Context Recall, Faithfulness, Answer Correctness | T-5.2 | `TODO` |
| T-5.4 | Custom Citation Accuracy (LLM-as-judge, FinGuard G-Eval pattern) | T-5.3 | `TODO` |
| T-5.5 | Four-class confusion matrix + **over-refusal counter as a first-class defect** (Finding 3) | T-5.2 | `TODO` |
| T-5.6 | Baseline run; record every number in the ledger | T-5.4, T-5.5 | `TODO` |

**Exit criterion (M5):** ledger populated with measured baselines. Until this milestone, the project has **no** numbers and none may be quoted anywhere.

**Blocked by T-1.8:** an item still carrying `[VERIFY]` cannot be promoted into the scored set.

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
| V-1 | India gratuity ceiling is `POINT_IN_TIME` — verify against the commencement provision of the Payment of Gratuity (Amendment) Act, 2018 | P-01 (marquee probe) | `OPEN` |
| V-2 | UAE Federal Law 8/1980 → Decree-Law 33/2021 transition mechanics for accrued gratuity | Best real straddle case; no golden answer until closed | `OPEN` |
| V-3 | DIFC / ADGM divergence from UAE mainland | P-17, R-12 | `OPEN` |
| V-4 | Indian state-level variation — verify one state, or scope corpus explicitly to "national baseline" and say so | Corpus scope statement | `OPEN` |
| V-5 | India Labour Codes commencement status | Already flagged in Tier-1 corpus note | `OPEN` |

---

## Results ledger

**Empty by design.** No row is written until a real run produces it. This section is the only place in the project where a number may originate; anything quoted elsewhere must trace back to a row here.

| Date | Milestone | Metric | Value | Run reference |
|---|---|---|---|---|
| — | — | — | *not yet measured* | — |

Metrics awaiting first measurement: Context Precision · Context Recall · Faithfulness · Answer Correctness · Citation Accuracy · four-class confusion matrix · over-refusal count · retrieval-only precision/recall (M3) · end-to-end latency · indexing cost.

---

## Risk register

| # | Risk | Phase | Mitigation |
|---|---|---|---|
| RK-1 | Synthetic corpus drifts to uniform, easy prose and stops being a real test | P1 | Defects-first build order; deliberate variation in drafting register; T-1.7 coverage audit |
| RK-2 | Guardrail threshold ratchets toward refuse-everything | P6 | Over-refusal counter gates T-6.6 |
| RK-3 | Deliberate fixtures get "fixed" by a later session | P1+ | `DELIBERATE_DEFECTS.md` manifest (T-1.1) written *before* the fixtures |
| RK-4 | OpenAI spend runs ahead of budget during indexing / eval loops | P2, P5 | Confirm key + balance at T-2.7; cache embeddings; dry-run mode for harness iteration |
| RK-5 | Drive API setup consumes a disproportionate share of D5 | P6 | T-6.1 can start any time — it has no upstream dependency; pull it forward if a phase runs short |
| RK-6 | Deployment pulls time from local-prototype quality | P8 | Held as fast-follow by design |
| RK-7 | Unmeasured claims leak into README or interview answers | All | Ledger is the single source of numbers; T-9.3 audits against it |

---

## Change log

| Date | Change |
|---|---|
| 2026-09-03 | Plan created. Phases 0–9, milestones M0–M9. |
| 2026-09-03 | Build order inverted — probes before corpus. Phase 1 restructured to build from the requirements spec rather than writing policy prose first. |
