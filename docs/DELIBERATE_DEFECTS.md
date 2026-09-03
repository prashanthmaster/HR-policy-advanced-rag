# Deliberate Defects Manifest

**Read this before "fixing" anything in `corpus/tier2_policy/`.**

Parts of this corpus are wrong on purpose. A non-compliant clause, a misleading worked example, a badly-drafted paragraph, a missing policy — each exists because a probe in `eval/golden/adversarial_probe_set.md` needs something to fail against. Remove one and the corresponding probe silently stops testing anything: it keeps passing, it just stops meaning anything. That is a worse outcome than a failing test, because nothing announces it.

This manifest is written **before** the fixtures it describes, so the intent is on record ahead of the artifact.

**Rule:** anything listed here may only be changed by first deleting or rewriting the probe that depends on it, in the same commit, with the reason stated. Never in isolation.

**Scope:** applies to Tier-2 (`corpus/tier2_policy/`, the fictional Meridian Global Services manual) only. Tier-1 (`corpus/tier1_law/`) is real statutory text and contains no deliberate defects — an error there is a genuine bug, fix it.

---

## D-1 · Policy clause below the statutory floor

| | |
|---|---|
| **Requirement** | R-11 |
| **Probe** | P-16 |
| **Failure mode** | FM-B4 |
| **Location** | Meridian India chapter — notice period, junior grades |

**The defect.** The clause sets a 15-day notice period for junior grades. Indian Model Standing Order 13 floors notice for a permanent workman at one month. The policy clause is therefore **unenforceable to the extent it undercuts the statutory minimum**.

**Why it exists.** P-16 tests conflict resolution in the direction that most systems get wrong. Its partner probe P-15 (policy *exceeds* the statutory floor → policy governs) has the opposite resolution. A system applying any single uniform rule — "the specific document wins," "the policy wins," "the statute wins" — passes exactly one of the pair. Both must pass, or the system has a coin-flip dressed as reasoning.

**Do not "correct" this to 30 days.** That destroys the asymmetry, and P-15/P-16 collapse into the same test.

**In-file marking.** The clause carries an inline comment recording that it is intentionally non-compliant, so a reader encountering it cold does not mistake it for careless drafting.

---

## D-2 · Decoy worked example

| | |
|---|---|
| **Requirement** | R-20 |
| **Probe** | P-34 |
| **Failure mode** | FM-D5 |
| **Location** | Meridian India chapter — gratuity, illustration adjacent to the normative clause |

**The defect.** A worked example computes gratuity for an employee earning **₹50,000/month** — the exact figure probe P-34 asks about. The illustration is deliberately written to be *more* lexically and semantically attractive to a retriever than the dry normative clause it illustrates: it is conversational, it contains the query's numbers, it reads like an answer.

**Why it exists.** Illustrations outranking the rules they illustrate is one of the most common silent failures in document RAG. The answer looks right, cites a real chunk from a real document, and passes a naive faithfulness check — while quoting an example's arithmetic as though it were the governing rule. The example must out-compete the clause on retrieval, or the probe tests nothing.

**Do not** rewrite the illustration to use a different salary, make it less prominent, or move it away from the clause. All three defuse it.

**Marking.** Tagged `normative: false`. The pipeline must never cite a `normative: false` chunk as authority. That tag is the fix; removing the decoy is not.

---

## D-3 · Low-salience clause

| | |
|---|---|
| **Requirement** | R-23 |
| **Probe** | FM-D8 (no dedicated probe — measured as retrieval recall on this clause) |
| **Location** | Meridian India chapter — leave encashment |

**The defect.** A clause written in dense, archaic drafting register ("emoluments in lieu of untaken privilege leave standing to credit upon cessation of engagement") that shares almost no vocabulary with how anyone would actually ask about it ("do I get paid for unused leave when I quit?").

**Why it exists.** Honest known-weakness probe. Real policy manuals contain clauses drafted decades apart in wildly different registers, and the badly-worded ones are exactly the ones retrieval loses. If this clause is always retrieved, the corpus is too easy and the eval numbers are flattering themselves.

**Do not** modernise the wording or add a plain-English summary beside it.

---

## D-4 · Missing paternity leave policy

| | |
|---|---|
| **Requirement** | R-25 |
| **Probe** | P-39 |
| **Failure mode** | FM-E3 |
| **Location** | Meridian leave chapters — **absent by design, all three countries** |

**The defect.** There is no paternity leave clause anywhere in the corpus. The surrounding leave chapters are otherwise complete — annual, sick, maternity, casual — which makes the absence conspicuous to a reader and, more importantly, creates high hallucination pressure: an LLM asked about paternity leave in a document set full of leave policies has every incentive to invent a plausible number.

**Why it exists.** P-39 is the corpus's primary hallucination probe. A fabricated entitlement here is undetectable by the employee asking, which is what makes it dangerous and what makes it worth testing.

**Do not add a paternity leave policy.** It is the highest-value absence in the corpus. If a future requirement genuinely needs one, add it to a *different* topic and leave this gap intact.

---

## D-5 · Deliberately incomplete governing-law clause

| | |
|---|---|
| **Requirement** | R-15 |
| **Probe** | P-14 |
| **Failure mode** | FM-B2 |
| **Location** | Meridian global preamble — applicable-law determination |

**The defect.** The governing-law clause addresses the straightforward case (employee working in their country of employment) and is **silent on the cross-border triangle** — nationality vs. work location vs. payroll entity. A German national on Indian payroll working from Dubai is not resolvable from the corpus.

**Why it exists.** P-14 is a `MUST_CLARIFY` probe. The correct behaviour is to identify that the corpus does not determine the answer and say so. If the clause resolved the triangle, the probe would become `MUST_ANSWER` and would stop testing the system's willingness to admit an undetermined case — which is the actual skill under test.

**Do not** complete this clause to cover cross-border cases.

---

## Summary

| ID | Fixture | Req | Probe | Destroyed by |
|---|---|---|---|---|
| D-1 | Sub-statutory notice clause | R-11 | P-16 | Raising it to the statutory minimum |
| D-2 | ₹50,000 decoy illustration | R-20 | P-34 | Changing the figure, or separating it from its clause |
| D-3 | Archaically-drafted clause | R-23 | FM-D8 | Modernising the wording |
| D-4 | Absent paternity leave | R-25 | P-39 | Adding the policy |
| D-5 | Incomplete governing-law clause | R-15 | P-14 | Completing it |

**Maintenance.** Any new deliberate defect gets a manifest entry in the same commit that introduces it. A fixture whose intent lives only in a commit message is a fixture that will be repaired by someone six weeks from now — most likely a future session of the assistant, acting helpfully and doing damage.
