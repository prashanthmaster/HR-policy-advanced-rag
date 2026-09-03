# Failure-Mode Register

**Method note.** This document was written *before* the Tier-2 policy corpus, deliberately. Questions first, documents second. A corpus written first and probed afterwards only ever tests what the author happened to think of while writing prose; a corpus written *to satisfy a failure register* is an instrument. Every Tier-2 policy clause that gets written from here on exists because some row in this table needs something to bite on.

**Scope of the claim.** This register is a design artifact, not a results table. Nothing here asserts that the system handles any of these — it asserts that these are the ways it can fail, and that each one has a probe. Which ones are actually handled is what the eval measures, and no row gets a "handled" mark until a real run says so.

---

## Part 1 — Three findings that come out of the adversarial pass and change the architecture

These are not failure modes. They are consequences of taking the failure modes seriously, and each one changes something structural. They are listed first because they affect the ingestion schema, which is the next thing to be built.

### Finding 1 — Temporal applicability is a *class*, not a date, and it cannot be inferred at retrieval time

The straddle case ("employee's service spans a policy change — split into two periods, compute each, sum") is the right instinct applied to the wrong universal. Splitting-and-summing is correct for *some* clause types and produces a confidently wrong number for others. Four distinct behaviours hide behind what looks like one question:

| Class | Rule | Worked example in this corpus |
|---|---|---|
| `POINT_IN_TIME` | The version in force **on the trigger-event date** governs the whole computation. No splitting. | India gratuity **ceiling**. Employee served 2014→2026 across the 2018-03-29 amendment; the ₹20,00,000 ceiling governs the entire payout. The pre-2018 ₹10,00,000 ceiling does **not** apply to the pre-2018 portion. |
| `SEGMENTED_ACCRUAL` | Service is cut at each amendment boundary; each segment computed under its own version; results summed. | A company leave-accrual rate that changes from 18 to 24 days/year effective mid-service. Entitlement genuinely splits. |
| `GRANDFATHERED` | Population-scoped. Old version continues to govern a cohort defined by a joining-date test; new version governs everyone else. Both versions are simultaneously current, for different people. | A policy amendment that applies "to employees joining on or after 1 Jan 2025." |
| `ELECTIVE` | Employee takes the more favourable of the two. Requires computing both and comparing. | Transitional provisions in some statutory changeovers. |

**The trap, stated plainly:** the intuitive answer to "employee's service spans the gratuity ceiling change" is split-and-sum, and it is wrong. A system that splits-and-sums *everything* is as broken as one that never splits — it just fails on a different half of the corpus. This is the single highest-value item in the whole probe set, because the naive-RAG answer and the naive-*human* answer are the same wrong answer.

**Architectural consequence:** a chunk needs `temporal_applicability` as a first-class metadata field, assigned at ingestion. It is not derivable from the clause text by the retriever, and it is not derivable by the generator from the retrieved text alone. If it isn't tagged, the straddle case is unanswerable no matter how good retrieval is — which means this is an *ingestion* problem masquerading as a retrieval problem.

**Consequence for the CRAG grading node:** its job widens. "Is this context sufficient?" is not just "does it contain the clause" — it is "does it contain the clause **and** the applicability rule governing how the clause maps onto this employee's timeline." A retrieval set containing both the old and new ceiling but no applicability rule is *insufficient*, and should trigger corrective re-query, not generation.

### Finding 2 — There are three clocks, and conflating any two of them silently corrupts the freshness layer

| Clock | Meaning | Source |
|---|---|---|
| `effective_date` | When the rule starts governing. A legal fact. | Stated inside the document text. |
| `revision_date` | When the document text last changed. | Google Drive `modifiedTime`. |
| `indexed_at` | When our pipeline last saw it. | Our own bookkeeping. |

The default failure of every "connect your RAG to Drive" tutorial is to use Drive's `modifiedTime` as though it were the effective date. It is not. Two cases break it in opposite directions:

- **Retroactive amendment.** Document edited 2026-06-01, clause states effective 2026-01-01. Six months of already-processed cases are now governed by a rule that did not exist when they were processed. `revision_date` is *later* than `effective_date`.
- **Future-dated amendment.** Document edited today, clause states effective 2027-01-01. A query asked today must be answered from the *current* clause and must *flag* the pending change. `revision_date` is *earlier* than `effective_date`. Naive semantic retrieval happily returns the future clause and answers from it — the system confidently tells an employee a rule that is not yet in force. This is the same class of error as answering from a superseded clause, pointed the other way in time, and it is the one most likely to survive to production unnoticed, because "the newest document" *feels* like the right answer.

**Consequence:** every retrieval must be filtered against an *as-of date* (default: today; overridable, because "what would this have been in March 2019" is a real HR question), and the filter is on `effective_date`, never on `revision_date`.

### Finding 3 — Faithfulness-as-guardrail has a degenerate optimum, and the eval as currently specified cannot see it

Reusing the Faithfulness score as the live refusal gate is a good design — one metric, two jobs. But Faithfulness alone is trivially maximised by refusing to answer anything. A system that answers "I cannot determine this from the available policy documents" to all 30 golden questions scores a perfect Faithfulness and passes the CI gate. There is no counter-pressure in the metric set as specified, so any threshold tuning is a one-way ratchet toward silence — and an HR assistant that refuses everything is not safe, it is useless, and it is *worse* than useless because it looks safe on the dashboard.

**Consequence — the golden set must be a labelled mixture, not a flat list.** Every item carries an expected-behaviour class:

- `MUST_ANSWER` — the answer is fully supported by the corpus. Refusing is a **failure**.
- `MUST_REFUSE` — the corpus genuinely does not support an answer. Answering is a failure.
- `MUST_CLARIFY` — a determinative fact is missing. Both answering and flatly refusing are failures.
- `MUST_FLAG` — answerable, but only with a mandatory caveat (superseded version exists / amendment pending / policy is below statutory floor).

Scored as a confusion matrix over these four classes, not as an average of scalar scores. **Over-refusal (`MUST_ANSWER` → refused) is tracked as a first-class defect with its own count**, and it is the metric that stops threshold tuning from ratcheting to silence. Answer Correctness restricted to the `MUST_ANSWER` subset is the natural counterweight to Faithfulness; the two must be reported together or neither means anything.

This does not add a fifth RAGAS metric — the four-plus-one metric set stays as locked. It changes how the *dataset* is labelled and how the gate is *computed*.

### Finding 4 (corollary) — not every document edit is an amendment

If the freshness layer treats every Drive `modifiedTime` change as a new version, then fixing a typo creates a spurious supersession event, the "this clause was amended on [date]" message fires on a formatting change, and the demo becomes noise. Re-indexing must classify the change:

`NO_OP` (whitespace/formatting) · `EDITORIAL` (typo, renumbering — text changed, meaning did not) · `SUBSTANTIVE` (meaning changed → new version, supersede predecessor) · `ADDITION` (new clause) · `SUNSET` (clause removed with no successor — see FM-A7)

Only `SUBSTANTIVE` and `SUNSET` create version events. This is also the honest answer to the interview question "what happens when someone fixes a comma in your source document?"

---

## Part 2 — The register

`REQ:` marks the corpus feature that must exist for the probe to be meaningful. These aggregate into the corpus requirements spec.

### Family A — Temporal & versioning
*The differentiator's own attack surface. If the system fails here it fails at the thing it exists to do.*

| ID | Failure mode | Why it breaks | Correct behaviour | REQ |
|---|---|---|---|---|
| FM-A1 | **Straddle service across an amendment** | Service spans an amendment boundary. System either ignores the boundary or splits when it shouldn't. | Apply the clause's `temporal_applicability` class (Finding 1). Show the working. | Clause pairs of each class |
| FM-A2 | **Retroactive amendment** | `effective_date` precedes `revision_date`. System dates the rule from when the file changed. | Govern from `effective_date`; flag that cases decided in the gap may need revisiting. | Policy amended with backdated effect |
| FM-A3 | **Future-dated amendment** | Newest document is not yet in force. Semantic search prefers it. | Answer from the currently-in-force clause; flag the pending change and its date. | Policy with future effective date |
| FM-A4 | **Grandfathered cohort** | Two versions are simultaneously current for different populations. | Determine cohort from joining date; if joining date unknown, this is `MUST_CLARIFY`. | Amendment scoped to joiners after a date |
| FM-A5 | **Silent supersession** | Superseded doc still sits in the Drive folder with no "superseded" marker. | Recognise supersession from version lineage, not from a marker in the text. | Two versions, old one left in place unmarked |
| FM-A6 | **Partial supersession** | One clause amended; rest of document unchanged and still current. Doc-level versioning marks the whole file stale. | Version at clause granularity. | Doc where only one clause changed |
| FM-A7 | **Sunset with no successor** | A temporary policy expired. Absence is the answer. | State the policy expired on [date] and no replacement exists. Do not fall back to a superficially similar live clause. | Expired temporary policy |
| FM-A8 | **Clause-number reuse** | v2 renumbers, so "Clause 7.2" means different things in different versions. | Cite version alongside clause number; never match on number alone. | Renumbering between versions |
| FM-A9 | **Vague effective date** | Policy says "with immediate effect" — from approval? publication? circulation? | Surface the ambiguity rather than silently picking one. | Clause with unresolvable effective date |

### Family B — Jurisdiction & conflict
*Multi-country is not three copies of one problem. The interactions are the problem.*

| ID | Failure mode | Why it breaks | Correct behaviour | REQ |
|---|---|---|---|---|
| FM-B1 | **Country unspecified, answer diverges** | Question is answerable in each country, differently. Highest-similarity chunk wins arbitrarily. | `MUST_CLARIFY`, or answer all three explicitly labelled. Never silently pick one. | Same topic, 3 divergent answers |
| FM-B2 | **Jurisdiction triangle** | Nationality ≠ work location ≠ payroll entity. German national, Indian payroll, working in Dubai. | Identify which axis governs for *this* entitlement; refuse to guess when the corpus doesn't say. | Policy clause on governing-law determination |
| FM-B3 | **Policy more generous than statute** | Policy grants 30 days notice where statute floors at 30 minimum. No conflict — policy governs. | Answer from policy; note it exceeds statutory minimum. | Policy above the floor |
| FM-B4 | **Policy *less* generous than statute** | Policy clause is void to the extent it undercuts the statutory floor. **Resolution is asymmetric with FM-B3.** | Answer from the *statute*; state the policy clause is unenforceable to that extent. | Policy below the floor (deliberate) |
| FM-B5 | **Sub-jurisdiction carve-out** | DIFC/ADGM free zones run separate employment regimes from UAE mainland. Indian labour law varies by state. | Detect the sub-jurisdiction; do not answer mainland law for a free-zone employee. | Free-zone annexe |
| FM-B6 | **Cross-country semantic contamination** | "Gratuity" embeds near-identically across India and UAE. Retriever returns the wrong country's clause. | Hard metadata filter on country, not a soft embedding preference. | Near-identical clauses, different numbers |
| FM-B7 | **Concept absent in jurisdiction** | Germany has no statutory gratuity. Absence is the correct answer. | State no equivalent entitlement exists; explain the nearest real construct without implying equivalence. | Already present: DE law note |
| FM-B8 | **Same term, different meaning** | "Probation" in India (Standing Orders) ≠ UAE Art. 9 ≠ German Probezeit. "Wages" base for gratuity differs. | Resolve the term within its jurisdiction before computing. | Definitions differing per country |

### Family C — Query pathology
*Real employees do not write clean queries. This family is where a demo-grade system dies on contact with users.*

| ID | Failure mode | Why it breaks | Correct behaviour | REQ |
|---|---|---|---|---|
| FM-C1 | **Underspecified query** | A determinative fact (country, joining date, tenure, wage) is missing. | `MUST_CLARIFY` — name the missing fact(s). Do not average over possibilities. | — |
| FM-C2 | **Contradictory premise** | "Resigned during probation after 6 years." Probation caps at 6 months everywhere in corpus. | Surface the contradiction; do not answer either reading as though it were coherent. | — |
| FM-C3 | **False premise stated as fact** | "As per our 60-day probation policy…" when policy says 6 months. | Correct the premise, then answer. Never inherit a false premise from the question. | Policy contradicting a plausible false premise |
| FM-C4 | **Broken / non-native phrasing** | "sir my notice how many day if i leaving now 2 year complete" — real register of a real user. | Answer as well as for clean phrasing. Retrieval must not degrade on malformed input. | — |
| FM-C5 | **Compound bundle** | Three questions with three different answers in one message. | Decompose and answer each, or clarify. Do not answer one and drop two. | — |
| FM-C6 | **Leading / confirmation-seeking** | "I get 90 days notice, right?" when the answer is 30. Sycophancy bait. | Contradict the user. Correctness outranks agreeableness. | — |
| FM-C7 | **Out-of-scope but plausible** | "Can I sue?" / "How do I structure this to avoid tax?" | Refuse the advice; give the policy fact. Stay inside the corpus. | — |
| FM-C8 | **Hypothetical vs actual conflation** | "If I had joined in 2017 what would my ceiling be" — a legitimate as-of-date query, not a current-state one. | Honour the as-of date; answer the counterfactual as a counterfactual. | Requires as-of-date retrieval (Finding 2) |

### Family D — Retrieval mechanics
*Ordinary RAG breakage. Unglamorous, and the most likely actual cause of a bad answer.*

| ID | Failure mode | Why it breaks | Correct behaviour | REQ |
|---|---|---|---|---|
| FM-D1 | **Numeric / slab-table lookup** | Embeddings are weak on numbers. "21 days" and "30 days" chunks are near-identical in vector space. | BM25 leg + structural table serialisation must carry this. Direct test of *why* hybrid over pure semantic. | Slab table (allowances by grade/tenure) |
| FM-D2 | **Proviso amputated from clause** | "Provided that…" lands in a different chunk. Answer states the rule and drops the exception — technically grounded, materially wrong. | Chunk boundaries must never separate a proviso from its clause. | Clause with a material proviso |
| FM-D3 | **Definition cross-reference chain** | Clause says "as defined in Section 2(s)". Definition is elsewhere and never retrieved. | Follow the reference or declare the context incomplete. | Cross-referencing definition |
| FM-D4 | **Acronym / synonym drift** | EOSB / EOSG / gratuity / end-of-service / severance / final settlement — same thing, different words per country. | Retrieval robust across the synonym set. | Deliberate vocabulary variation |
| FM-D5 | **Illustration-vs-normative decoy** | A worked example ("e.g. an employee earning ₹50,000…") looks *more* query-like than the dry normative clause. Reranker prefers it. Answer cites the illustration's numbers as the rule. | Retrieve the normative clause; illustrations tagged non-normative and never cited as authority. | Worked example beside its clause |
| FM-D6 | **Near-duplicate version crowding** | v1 and v2 of a clause are ~95% identical; both flood top-k; the actual answer is squeezed out. | Deduplicate by lineage before rerank; diversity constraint on top-k. | Minimally-differing version pair |
| FM-D7 | **Multi-hop arithmetic** | Gratuity needs tenure + wage base definition + rate + ceiling from ≥3 chunks. Recall on any one of them is a wrong number, not a missing answer. | All operands retrieved, or refuse. Partial retrieval must not produce a confident partial computation. | Operands deliberately scattered |
| FM-D8 | **Long-tail rare clause** | A clause nothing is phrased like — low lexical and semantic salience. | Should still be reachable. Honest known-weakness probe. | An oddly-worded clause |

### Family E — Answer integrity & guardrail
*What reaches the user.*

| ID | Failure mode | Why it breaks | Correct behaviour | REQ |
|---|---|---|---|---|
| FM-E1 | **Version blending** | Old and new text merged into one fluent sentence. **The headline failure this project exists to prevent.** | Never. One version, explicitly dated, or an explicit statement of the change. | Version pair |
| FM-E2 | **Citation drift** | Right answer, wrong citation. Invisible to Faithfulness. | Cite the clause the number actually came from. This is what Citation Accuracy exists to catch. | — |
| FM-E3 | **Fabricated figure** | A plausible number appearing nowhere in the corpus. | Guardrail catches; refuse. | — |
| FM-E4 | **Over-refusal** | Declines when the answer is plainly present. The guardrail's own failure mode (Finding 3). | Answer. Tracked as a first-class defect. | `MUST_ANSWER` subset |
| FM-E5 | **Unflagged assumption** | Silently assumes India because most of the corpus is Indian. Answer is fluent, confident, and about the wrong country. | State assumptions explicitly, or clarify. | — |
| FM-E6 | **Stale confidence** | Answers correctly from the current clause but never mentions that a superseded version exists — user with an old handbook has no idea why the numbers differ. | Flag the supersession when one exists in lineage. | Version pair |

---

## Part 3 — Open verification items

Under the project ground rule, these are flagged rather than asserted. None becomes a golden answer until checked against a primary source.

1. **India gratuity ceiling is `POINT_IN_TIME`.** The reading applied above — the ceiling in force at the date gratuity becomes payable governs the entire payout, with no pro-rating across an employee's pre- and post-amendment service — is the standard understanding of the 2018 amendment's commencement. Verify against the commencement provision of the Payment of Gratuity (Amendment) Act, 2018 before locking the worked example.
2. **UAE 1980 → 2021 transition mechanics.** How gratuity accrued under Federal Law 8/1980 is treated on transition to Decree-Law 33/2021 is exactly a `SEGMENTED_ACCRUAL`-vs-`POINT_IN_TIME` question, and it would be the best real straddle case in the corpus. Transitional provisions not yet checked. **Do not write a golden answer for this until verified.**
3. **DIFC / ADGM divergence (FM-B5).** Free zones are known to run separate employment regimes. Specific divergences not yet verified.
4. **Indian state-level variation.** Standing Orders and shops-and-establishments rules vary by state. The corpus currently treats a national baseline. Either verify a state or scope the corpus explicitly to "national baseline" and say so.
5. **India Labour Codes commencement.** Already flagged in the Tier-1 India corpus note. Unchanged.
