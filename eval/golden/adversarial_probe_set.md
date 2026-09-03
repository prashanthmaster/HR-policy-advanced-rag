# Adversarial Probe Set

Derived from `docs/FAILURE_MODES.md`. **These questions were written before the Tier-2 policy corpus exists** — the corpus is then built so that each probe has something real to bite on.

**Status: probes only.** Expected behaviour is specified; golden *answers* are not filled in until (a) the corpus clause exists and (b) any statutory reading is verified per the register's Part 3. A probe with a `[VERIFY]` tag must not be promoted into the scored golden set until that verification is done.

**Classes:** `MUST_ANSWER` · `MUST_REFUSE` · `MUST_CLARIFY` · `MUST_FLAG` (answerable, but a mandatory caveat is part of correctness).

Questions are written in the register real employees use, not in clean legal English. That is deliberate — see FM-C4.

---

## The marquee probe

**P-01 · FM-A1, FM-D7, FM-E2 · `MUST_ANSWER`**

> "I joined 1 Jan 2014 and I'm resigning 30 Sep 2026. Basic + DA is ₹3,00,000/month. India. What gratuity do I get?"

V-1 closed 2026-09-03 — see `PROJECT_PLAN.md` Verification register. Unblocked for the scored golden set.

*Why this is the best item in the set:* the intuitive answer is wrong, and it is wrong in the same direction for a naive RAG and a naive human. Service spans the 2018-03-29 ceiling amendment (₹10L → ₹20L), so the tempting move is to split service at the boundary and blend two ceilings.

- **The trap answer** (split-and-sum the ceiling): compute ~4.2 years under a ₹10L ceiling and ~8.5 years under ₹20L, blend. Any number produced this way is wrong.
- **Expected:** ceiling is `POINT_IN_TIME` — the version in force at the date gratuity becomes payable governs the *entire* payout. Formula: (300000 ÷ 26) × 15 × 13 completed years = ₹22,50,000, capped at the ceiling in force on 2026-09-30 → **₹20,00,000**.
- **Must also:** show the working, cite the formula clause and the ceiling clause separately, and state which ceiling applied and why the pre-2018 ceiling did not.
- **Contrast probe P-02** — same shape, opposite class.

**P-02 · FM-A1 · `MUST_ANSWER`**

> "Our leave policy changed from 18 to 24 days a year partway through my service. I've been here the whole time. How many days did I accrue?"

Same surface shape as P-01, opposite applicability class. This one **is** `SEGMENTED_ACCRUAL`: split at the amendment boundary, compute each segment under its own rate, sum. A system that learned "don't split" from P-01 fails here; a system that learned "always split" fails P-01. Both probes must pass together or the model has pattern-matched instead of reasoned.

**P-03 · FM-A1, FM-B8 · `MUST_ANSWER`**

> "Dubai. 7 years service. How is my end of service calculated?"

Third shape in the family, and the one that catches over-correction: UAE gratuity **is** segmented (21 days/year for the first 5 years, 30 days/year after) — but segmented by **tenure band**, not by amendment date. Splitting is correct here for a reason unrelated to versioning. Tests whether the system distinguishes *why* it is splitting.

**P-3a · FM-A1, FM-B5, FM-D7 · `MUST_ANSWER`**

> "I've been with the DIFC entity since 2017 and I'm leaving this year. What's my end of service?"

**The best straddle case in the corpus, and it is entirely real.** DIFC replaced end-of-service gratuity with the DEWS defined-contribution scheme on **1 February 2020**. Service before that date remains payable as legacy gratuity on the old 21/30-day basis; service from that date accrues as employer contributions (5.83% of basic rising to 8.33% after five years). An employee with 2017→2026 service receives **both components**, covering two consecutive segments of one continuous service.

- **Expected:** split at 2020-02-01, compute each segment on its own basis, state both, and do not blend them into a single formula.
- **Why it matters:** this is `SEGMENTED_ACCRUAL` in real statute — and it sits directly against P-01, which is `POINT_IN_TIME` in real statute and must *not* be split. Two genuine straddle cases, opposite correct answers, both independently checkable by an interviewer. Neither is invented.

**P-3b · FM-B5, FM-B8, FM-D1 · `MUST_ANSWER`**

> "How much annual leave do I get? I'm in Dubai."

A unit trap inside a single city. DIFC grants **20 working days**; UAE mainland grants **30 calendar days**. Same words, same country, different units, and the smaller number is not the smaller entitlement once converted. An answer that reports a figure without its unit, or that compares the two by magnitude, is wrong even when it retrieves the right clause.

---

## Family A — Temporal & versioning

| ID | FM | Probe | Class | Expected behaviour |
|---|---|---|---|---|
| P-04 | A2 | "Policy doc says effective 1 Jan 2026 but it was only uploaded last week. I was terminated in March. Which applies to me?" | `MUST_FLAG` | Govern from `effective_date`, not upload date. Flag that March falls in the retroactive window and the case may need revisiting. |
| P-05 | A3 | "What's my notice period?" *(corpus contains a future-dated amendment not yet in force)* | `MUST_FLAG` | Answer from the **currently in-force** clause. Flag the pending change and its effective date. Answering from the newest document is a failure. |
| P-06 | A4 | "My colleague in Dubai gets an end-of-service supplement on top of gratuity. HR says I don't get it. Who's right?" | `MUST_CLARIFY` | Both are right, under a grandfathered amendment: the supplement survives for service commencing before 2025-01-01 only. Cohort turns on joining date — which the query does not supply. Name the missing fact. |
| P-07 | A5 | "What's the current probation period?" *(superseded doc left sitting in the Drive folder, unmarked)* | `MUST_ANSWER` | Answer from the current version. Supersession must be recognised from lineage, not from any marker in the text. |
| P-08 | A6 | "Has our leave policy changed?" *(only clause 7.2 of the doc was amended)* | `MUST_ANSWER` | Identify the one amended clause. Do not report the whole document as changed. |
| P-09 | A7 | "What's the WFH allowance?" *(temporary policy, expired, no successor)* | `MUST_REFUSE` | State the policy expired on [date] with no replacement. Must **not** substitute a superficially similar live clause. |
| P-10 | A8 | "What does clause 7.2 say?" *(number reused across versions with different content)* | `MUST_CLARIFY` | Ambiguous across versions. Ask which version, or answer both explicitly versioned. Never match on clause number alone. |
| P-11 | A9 | "The policy says 'with immediate effect' — effective from when exactly?" | `MUST_FLAG` | Surface the ambiguity (approval vs publication vs circulation). Do not silently pick one. |
| P-12 | C8/A1 | "If I had joined in 2017 instead, what gratuity ceiling would apply to me?" | `MUST_ANSWER` | As-of-date reasoning. Joining year does not change the ceiling — the ceiling at *payout* does. Tests whether the system understands the rule or just pattern-matches dates. |

## Family B — Jurisdiction & conflict

| ID | FM | Probe | Class | Expected behaviour |
|---|---|---|---|---|
| P-13 | B1 | "How many days notice do I need to give?" *(no country stated)* | `MUST_CLARIFY` | Three materially different answers exist. Clarify, or answer all three explicitly labelled. Silently picking one is the failure. |
| P-14 | B2 | "I'm a German national on the Indian payroll but I work out of the Dubai office. Which notice period applies?" | `MUST_CLARIFY` | The jurisdiction triangle. Identify which axis governs, or state the corpus doesn't determine it. Picking one axis silently is the failure. |
| P-15 | B3 | "Company policy gives 45 days notice but I heard the law says 30. Which one do I get?" | `MUST_ANSWER` | Policy exceeds the statutory floor → policy governs. Note it is above the minimum. |
| P-16 | B4 | "Policy says 15 days notice for my grade. Is that what I get?" *(statute floors at 30)* | `MUST_ANSWER` | **Asymmetric with P-15.** Statute governs; the policy clause is unenforceable to the extent it undercuts the floor. A system that applies "the specific document wins" uniformly fails exactly one of P-15/P-16. |
| P-17 | B5 | "I'm in the DIFC office. Same rules as the rest of UAE?" | `MUST_FLAG` | Separate regime (DIFC Law No. 2 of 2019). Notice at 5+ yrs is 90 days, not 30; leave is 20 *working* days, not 30 *calendar*; end-of-service is DEWS, not gratuity. Must not answer mainland law. **Verified 2026-09-03.** Note the trap in the question: "in the DIFC office" describes a *location*, but the governing regime follows the employing entity — so strictly this is `MUST_CLARIFY` if the entity is unstated. |
| P-18 | B6 | "What's the gratuity in Germany?" | `MUST_REFUSE` | No statutory equivalent. Must not return the India or UAE clause — the strongest semantic-contamination probe in the set, because "gratuity" embeds nearly identically across countries. |
| P-19 | B8 | "How long is probation?" *(no country)* | `MUST_CLARIFY` | Same word, three different legal constructs and durations. |
| P-20 | B6/D1 | "Is my gratuity calculated on basic or total salary?" | `MUST_CLARIFY` | Wage base differs by country. Country determines the answer. |

## Family C — Query pathology

| ID | FM | Probe | Class | Expected behaviour |
|---|---|---|---|---|
| P-21 | C1 | "What's my gratuity?" | `MUST_CLARIFY` | Missing: country, tenure, wage. Name all three. Do not answer with a formula and hope. |
| P-22 | C2 | "I resigned during probation after 6 years of service — what's my notice?" | `MUST_CLARIFY` | Incoherent: probation caps at 6 months in all three jurisdictions. Surface the contradiction rather than answering either reading. |
| P-23 | C3 | "As per our 60-day probation policy, when do I get confirmed?" | `MUST_ANSWER` | False premise. Correct it first (policy says 6 months), then answer. Inheriting the premise is the failure. |
| P-24 | C4 | "sir my notice how many day if i leaving now 2 year complete india" | `MUST_ANSWER` | Must perform as well as on clean phrasing. Retrieval degradation on malformed input is the failure. |
| P-25 | C4 | "eosb kitna milega 5 saal ke baad dubai" *(transliterated Hindi/Urdu — realistic for a Gulf workforce)* | `MUST_ANSWER` | Same answer as the clean-English equivalent. |
| P-26 | C5 | "What's my notice period, gratuity, and leave balance if I resign next month?" | `MUST_CLARIFY` | Three questions, three answers. Decompose. Answering one and dropping two is the failure. |
| P-27 | C6 | "I'm entitled to 90 days notice, right?" *(answer is 30)* | `MUST_ANSWER` | Contradict the user plainly. Sycophantic agreement is the failure. |
| P-28 | C6 | "HR says I get nothing since I left before 5 years. That's illegal, isn't it?" | `MUST_FLAG` | Answer the policy fact (5-year rule, with its death/disablement exception). Do not endorse or reject the legal characterisation. |
| P-29 | C7 | "How should I structure my resignation date to minimise tax on gratuity?" | `MUST_REFUSE` | Out of scope. State the policy facts; decline the tax-structuring advice. |

## Family D — Retrieval mechanics

| ID | FM | Probe | Class | Expected behaviour |
|---|---|---|---|---|
| P-30 | D1 | "Grade M3, 6 years, Dubai — what's my housing allowance?" *(slab table)* | `MUST_ANSWER` | Exact cell from a two-dimensional table. Direct test of the hybrid retrieval rationale: pure semantic will not reliably land the right row+column. |
| P-31 | D2 | "Do I get gratuity if I was terminated for misconduct?" | `MUST_ANSWER` | The proviso, not the main clause, is the answer. Stating the general rule and omitting the exception is grounded-but-wrong — the exact failure Faithfulness alone will not catch. |
| P-32 | D3 | "What counts as 'wages' for my gratuity?" *(definition in a different section)* | `MUST_ANSWER` | Follow the cross-reference, or declare context incomplete. |
| P-33 | D4 | "What's my long service award?" / "What's my loyalty payment?" / "What's my continuity recognition?" *(three phrasings, one answer — corrected 2026-09-03: original wording used Gulf EOSB terminology that matches none of the fixture's actual synonym set; MER-IN-LONGSERVICE-AWARD's real four names are long service award / loyalty payment / continuity recognition / service milestone grant)* | `MUST_ANSWER` | All three retrieve the same clause. Divergent answers across synonyms is the failure. **Likely explains the P-33 zero-recall result in the Phase 3 M3 run — the old query terms did not appear in the fixture at all, so that was a probe/fixture mismatch, not a demonstrated retrieval failure.** |
| P-34 | D5 | "How much gratuity for someone earning ₹50,000 a month?" *(a worked example in the corpus uses exactly ₹50,000)* | `MUST_ANSWER` | Must cite the **normative clause**, not the illustration. Illustrations are tagged non-normative and must never be cited as authority — even when they match the query far better lexically. |
| P-35 | D6 | "What's the notice period?" *(v1 and v2 ~95% identical, both flood top-k)* | `MUST_ANSWER` | Deduplicate by lineage before rerank so the answer is not crowded out by its own near-duplicate. |
| P-36 | D7 | "Full and final settlement for 8 years in Dubai on 20,000 AED basic?" | `MUST_ANSWER` | Operands scattered across ≥3 clauses (rate bands, wage base, 2-year cap). Partial retrieval must refuse, not produce a confident partial computation. |

## Family E — Answer integrity

| ID | FM | Probe | Class | Expected behaviour |
|---|---|---|---|---|
| P-37 | E1 | "What's the maximum gratuity payable in India?" | `MUST_ANSWER` + `MUST_FLAG` | ₹20,00,000, effective 2018-03-29. **Never** a sentence blending ₹10L and ₹20L. The headline probe. |
| P-38 | E6 | "My old handbook says ₹10 lakh, is that right?" | `MUST_FLAG` | Explain the supersession and its date. Answering "₹20 lakh" without acknowledging why their handbook differs is technically correct and practically useless. |
| P-39 | E3 | "What's the paternity leave entitlement?" *(absent from corpus)* | `MUST_REFUSE` | Refuse. High hallucination pressure — a plausible number is easy to invent and impossible for the user to check. |
| P-40 | E4 | "What is the notice period during probation in the UAE?" | `MUST_ANSWER` | 14 days, Art. 9(1). Unambiguous, single clause, plainly present. **Over-refusal here is a defect**, and this probe exists specifically to stop threshold tuning from ratcheting toward silence (Finding 3). |
| P-41 | E5 | "How much notice do I owe?" *(corpus is India-heavy)* | `MUST_CLARIFY` | Must not default to India because the corpus leans that way. Fluent, confident, wrong-country answers are the failure. |

---

## Amendments to this set

**2026-09-03 — P-06 rewritten (fixture collision).** As originally written, P-06 tested a *grandfathered* amendment using the same 18→24 annual-leave change that P-02 uses to test *segmented accrual*. One fixture cannot carry both mechanics: a leave rate that splits service at the boundary is not a leave rate that persists for one cohort and not another, and building both against the same clause would have made whichever probe ran second meaningless.

Caught during corpus construction (T-1.3), which is the reverse-engineering loop running the other way — the corpus validating the probe set rather than the probe set specifying the corpus. Resolution: P-02 keeps annual leave (India, `SEGMENTED_ACCRUAL`, R-01); P-06 moves to the UAE end-of-service supplement (`GRANDFATHERED`, R-02, cohort boundary 2025-01-01). Both mechanics are now tested, on separate fixtures, in different jurisdictions.

---

## Coverage and composition

43 probes over 39 failure modes. Target composition for the scored golden set (20–30 items drawn from these, per the locked eval design):

| Class | Share | Purpose |
|---|---|---|
| `MUST_ANSWER` | ~45% | Counterweight to Faithfulness; over-refusal detector |
| `MUST_CLARIFY` | ~25% | Stateless clarification contract (below) |
| `MUST_FLAG` | ~20% | Versioning/supersession behaviour |
| `MUST_REFUSE` | ~10% | Hallucination + scope discipline |

An all-`MUST_ANSWER` set cannot detect hallucination; an all-`MUST_REFUSE` set scores a silent system perfectly. The mixture is the instrument.

---

## Design consequence: stateless clarification

`MUST_CLARIFY` is ~25% of the set, which appears to collide with the locked scope decision — no chatbot, no conversational memory, stateless single-turn.

It does not. **Clarification is not conversation.** The system does not ask a question and wait; it returns, in one turn, a structured terminal response:

```
status: NEEDS_CLARIFICATION
missing_facts:
  - country_of_employment   (determinative: notice differs 30d / 14d-probation / 4wk+)
  - date_of_joining         (determinative: grandfathered cohort boundary 2025-01-01)
conditional_answers:
  - if country=UAE  and joined>=2025-01-01 → 30 days (DL33/2021 Art.43) [+ policy clause]
  - if country=India and joined< 2025-01-01 → 30 days (Model SO 13)     [+ policy clause]
provisional_citations: [...]
```

The user re-asks with the missing fact. Nothing is remembered between turns; the second query is independent and self-contained. This preserves the stateless design *and* handles the underspecified query — and it is a stronger interview answer than either "we ask a follow-up question" (breaks the stated architecture) or "we refuse" (useless to the employee).

It also makes clarification **scorable**, which a conversational probe would not be: the golden answer for a `MUST_CLARIFY` item is the *set of missing facts*, checkable exactly.
