# Meridian Global Services (India) Private Limited — HR Policy Manual

> ⚠️ **SYNTHETIC DOCUMENT — NOT A REAL COMPANY POLICY.**
> Meridian Global Services is a fictional entity. This chapter exists to exercise a retrieval system against realistic policy structure and must never be represented as a real HR policy or as legal guidance. Real Indian statutory law used by this project is in `corpus/tier1_law/india/india_law.md`, separately sourced and cited.

**Build status:** partial. This file is built incrementally against `docs/CORPUS_REQUIREMENTS.md`. Currently contains T-1.2 deliberate-defect fixtures only. Version-pair, conflict, and retrieval-mechanic structures follow in T-1.3 → T-1.5; ordinary connective prose in T-1.6.

---
clause_id: MER-IN-NOTICE-SENIOR
lineage_id: MER-IN-NOTICE-SENIOR
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 4.1
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: india-national
---
An employee in Grade M1 or above who wishes to resign shall give the Company forty-five (45) days' written notice, or payment of basic salary in lieu of the unexpired portion of that notice. The Company shall give the same period of notice where it terminates the engagement of such an employee otherwise than for misconduct.

---
clause_id: MER-IN-NOTICE-JUNIOR
lineage_id: MER-IN-NOTICE-JUNIOR
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 4.2
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: india-national
deliberate_defect: D-1
---
<!-- DELIBERATE DEFECT D-1 (req R-11, probe P-16, failure mode FM-B4).
     This clause is INTENTIONALLY NON-COMPLIANT. It sets 15 days' notice where
     Model Standing Order 13 floors notice for a permanent workman at one month,
     so it is unenforceable to the extent it undercuts the statutory minimum.
     It is the deliberate counterpart to MER-IN-NOTICE-SENIOR (which sits ABOVE
     the floor, probe P-15) — the pair tests that conflict resolution is
     asymmetric rather than a single uniform "specific document wins" rule.
     DO NOT raise this to 30 days. See docs/DELIBERATE_DEFECTS.md. -->
An employee in Grade A1 to A3 who wishes to resign shall give the Company fifteen (15) days' written notice, or payment of basic salary in lieu of the unexpired portion of that notice. The same period shall apply where the Company terminates the engagement of such an employee otherwise than for misconduct.

---
clause_id: MER-IN-GRATUITY-ENTITLEMENT
lineage_id: MER-IN-GRATUITY-ENTITLEMENT
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 6.1
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: india-national
references: [IN-GRAT-S4-ELIG, IN-GRAT-S4-FORMULA, IN-GRAT-S4-CEILING]
---
An employee who has rendered continuous service of not less than five years is entitled on cessation of employment to gratuity computed in accordance with the Payment of Gratuity Act, 1972, namely fifteen days' wages (last drawn basic salary and dearness allowance) for each completed year of service, a part of a year in excess of six months being reckoned as a completed year. The amount so computed is subject to the statutory maximum in force on the date the gratuity becomes payable. The five-year qualifying condition does not apply where cessation is by reason of death or disablement.

---
clause_id: MER-IN-GRATUITY-ILLUSTRATION
lineage_id: MER-IN-GRATUITY-ILLUSTRATION
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 6.1 — Illustration (explanatory only)
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: false
jurisdiction_scope: india-national
illustrates: MER-IN-GRATUITY-ENTITLEMENT
deliberate_defect: D-2
---
<!-- DELIBERATE DEFECT D-2 (req R-20, probe P-34, failure mode FM-D5).
     This illustration is INTENTIONALLY the more retrievable chunk: it is
     conversational, it contains the exact figure P-34 asks about (Rs 50,000),
     and it reads like a finished answer. It also OMITS the statutory ceiling
     entirely — harmless here because the ceiling does not bite at this salary,
     but materially wrong if generalised into a rule, which is precisely the
     failure being tested. normative: false — the pipeline must never cite this
     as authority. DO NOT change the salary figure, add the ceiling, or move it
     away from clause 6.1. See docs/DELIBERATE_DEFECTS.md. -->
**How much gratuity will I get? A worked example.** Suppose an employee's last drawn basic salary plus dearness allowance is ₹50,000 per month, and the employee has completed 10 years and 7 months of continuous service with the Company. Because the part-year of 7 months exceeds six months, it counts as a full year, so the service is reckoned as 11 years. The calculation is: (₹50,000 ÷ 26) × 15 × 11 = **₹3,17,308** (rounded to the nearest rupee). This amount is paid within thirty days of cessation of employment.

---
clause_id: MER-IN-LEAVE-ENCASHMENT
lineage_id: MER-IN-LEAVE-ENCASHMENT
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 5.7
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: india-national
deliberate_defect: D-3
---
<!-- DELIBERATE DEFECT D-3 (req R-23, failure mode FM-D8).
     INTENTIONALLY drafted in a dense archaic register sharing almost no
     vocabulary with how this would actually be asked ("do I get paid for my
     unused leave when I quit?"). Honest known-weakness probe for retrieval of
     low-salience clauses. DO NOT modernise the wording or add a plain-English
     summary beside it. See docs/DELIBERATE_DEFECTS.md. -->
Emoluments in lieu of untaken privilege leave standing to the credit of a workman upon cessation of engagement shall be discharged at the substantive rate of basic remuneration obtaining at the date of such cessation, computed upon the aggregate of days so standing, provided that the aggregate in respect of which such discharge is made shall not in any event exceed forty-five days, and provided further that no such discharge shall be made in respect of casual or sick leave, howsoever accrued or unavailed.

---
## Leave types covered by this chapter

Section 5 of this Manual addresses: annual/privilege leave (5.1), casual leave (5.2), sick leave (5.3), maternity leave (5.4), bereavement leave (5.5), unpaid leave (5.6), and leave encashment on cessation (5.7).

<!-- DELIBERATE DEFECT D-4 (req R-25, probe P-39, failure mode FM-E3).
     There is NO paternity leave clause in this chapter, or in the UAE or
     Germany chapters. The absence is the fixture: the surrounding leave
     coverage is otherwise complete, which creates maximum hallucination
     pressure for P-39. DO NOT ADD A PATERNITY LEAVE POLICY.
     See docs/DELIBERATE_DEFECTS.md. -->

---
clause_id: MER-IN-LEAVE-ANNUAL-V1
lineage_id: MER-IN-LEAVE-ANNUAL
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 5.1
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: SEGMENTED_ACCRUAL
superseded_by: MER-IN-LEAVE-ANNUAL-V2
normative: true
jurisdiction_scope: india-national
corpus_requirement: R-01
---
A confirmed employee accrues privilege leave at the rate of eighteen (18) days for each completed year of service, accruing proportionately month by month. Privilege leave may be carried forward to a maximum of forty-five (45) days.

---
clause_id: MER-IN-LEAVE-ANNUAL-V2
lineage_id: MER-IN-LEAVE-ANNUAL
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 5.1
effective_date: 2024-07-01
revision_date: 2024-06-14
version: v2
temporal_applicability: SEGMENTED_ACCRUAL
supersedes: MER-IN-LEAVE-ANNUAL-V1
normative: true
jurisdiction_scope: india-national
corpus_requirement: R-01
---
A confirmed employee accrues privilege leave at the rate of twenty-four (24) days for each completed year of service, accruing proportionately month by month. Privilege leave may be carried forward to a maximum of forty-five (45) days. **Leave accrued in respect of service rendered before 1 July 2024 is unaffected by this revision and remains credited at the rate then applicable.** For an employee in service on that date, entitlement is therefore computed at the former rate for service up to 30 June 2024 and at the revised rate thereafter.

---
clause_id: MER-IN-SHIFT-ALLOWANCE
lineage_id: MER-IN-SHIFT-ALLOWANCE
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 8.4
effective_date: 2026-01-01
revision_date: 2026-06-01
version: v2
supersedes: MER-IN-SHIFT-ALLOWANCE-V1
temporal_applicability: SEGMENTED_ACCRUAL
normative: true
jurisdiction_scope: india-national
corpus_requirement: R-04
---
<!-- R-04 retroactive amendment (probe P-04, failure mode FM-A2): effective_date
     2026-01-01 PRECEDES revision_date 2026-06-01. A pipeline that treats Drive
     modifiedTime as the effective date will date this rule from June and get
     five months of cases wrong. -->
The night shift allowance payable to employees rostered on the 22:00–06:00 shift is revised to ₹750 per shift, **with effect from 1 January 2026**. This revision was approved and published on 1 June 2026. Arrears in respect of shifts worked between the effective date and the date of publication shall be computed and paid in the payroll cycle following publication.

---
clause_id: MER-IN-SHIFT-ALLOWANCE-V1
lineage_id: MER-IN-SHIFT-ALLOWANCE
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 8.4
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
superseded_by: MER-IN-SHIFT-ALLOWANCE
temporal_applicability: SEGMENTED_ACCRUAL
normative: true
jurisdiction_scope: india-national
corpus_requirement: R-04
---
The night shift allowance payable to employees rostered on the 22:00–06:00 shift is ₹500 per shift.

---
clause_id: MER-IN-WFH-ALLOWANCE
lineage_id: MER-IN-WFH-ALLOWANCE
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual — Temporary Measures Annexe
section: TM-3
effective_date: 2021-04-01
revision_date: 2021-04-01
sunset_date: 2023-03-31
version: v1 (EXPIRED)
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: india-national
corpus_requirement: R-07
---
<!-- R-07 sunset with no successor (probe P-09, failure mode FM-A7). This policy
     EXPIRED on 2023-03-31 and was deliberately not replaced. Correct behaviour
     for a query about WFH allowance is to state that it expired and no
     replacement exists — NOT to substitute a superficially similar live
     allowance clause. Do not add a successor policy. -->
**Temporary measure.** An employee required to work from home is entitled to a work-from-home allowance of ₹2,000 per month toward connectivity and utilities. This measure is issued under the Temporary Measures Annexe and **shall cease to have effect on 31 March 2023** unless expressly extended by the Group People Committee. No extension was issued.

---
clause_id: MER-IN-RELOCATION
lineage_id: MER-IN-RELOCATION
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 9.2
effective_date: UNRESOLVED
revision_date: 2025-11-20
version: v2
temporal_applicability: POINT_IN_TIME
effective_date_ambiguity: true
normative: true
jurisdiction_scope: india-national
corpus_requirement: R-09
---
<!-- R-09 vague effective date (probe P-11, failure mode FM-A9). The amending
     instrument says "with immediate effect" without specifying whether that
     means the date of Committee approval, the date of publication, or the date
     of circulation to employees — and the three differ. The ambiguity must
     SURVIVE ingestion rather than being silently resolved to one of them.
     effective_date is recorded as UNRESOLVED deliberately. -->
The domestic relocation grant is revised to one month's basic salary, **with immediate effect**. (Approved by the Group People Committee on 12 November 2025; published to the intranet on 20 November 2025; circulated to line managers on 1 December 2025.)

---
clause_id: MER-IN-PROBATION
lineage_id: MER-IN-PROBATION
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 3.4
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: india-national
corpus_requirement: R-24
---
<!-- R-24 false-premise bait (probe P-23). Probation is stated plainly as six
     months, which makes "our 60-day probation policy" checkably false. The
     system must correct the premise before answering, not inherit it. -->
A new employee is engaged on probation for a period of six (6) months from the date of joining. The Company may extend the probation by a further period not exceeding three (3) months where performance during the initial period has not been satisfactory. An employee remains a probationer until confirmed in writing; confirmation is not automatic on expiry of the probation period.

---
clause_id: MER-IN-GRATUITY-FORFEITURE
lineage_id: MER-IN-GRATUITY-FORFEITURE
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 6.2
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: india-national
corpus_requirement: R-17
references: [IN-GRAT-S4-6-FORFEITURE]
---
<!-- R-17 material proviso (probe P-31, failure mode FM-D2). THE CHUNKER MUST NOT
     SPLIT THIS. The general rule and its provisos are separated by blank lines
     precisely so a naive paragraph-splitting chunker WILL separate them — that
     is the test. An answer stating the general rule and omitting the provisos is
     grounded in a real retrieved chunk and materially wrong, which is the
     failure Faithfulness alone cannot catch. -->
Gratuity is payable to an employee on cessation of employment in accordance with clause 6.1 and the Payment of Gratuity Act, 1972.

Provided that where an employee's services are terminated for any act, wilful omission or negligence causing damage or loss to Company property, gratuity shall be forfeited to the extent of the damage or loss so caused, and not further.

Provided further that where an employee's services are terminated for riotous or disorderly conduct, any other act of violence, or an offence involving moral turpitude committed in the course of employment, gratuity may be forfeited wholly or in part at the Company's discretion.

Provided also that no forfeiture shall be made under either proviso unless the termination was itself effected on the ground relied upon, and unless the employee has been given an opportunity to be heard.

---
clause_id: MER-IN-DEFN-WAGES
lineage_id: MER-IN-DEFN-WAGES
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual — Chapter 2, Definitions
section: 2.14
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: india-national
corpus_requirement: R-18
---
<!-- R-18 cross-referenced definition (probe P-32, failure mode FM-D3). Lives in
     Chapter 2, referred to from Chapter 6 (gratuity) and Chapter 8 (allowances)
     without being restated. Retrieval returning only the gratuity clause has an
     incomplete context and must follow the reference or declare insufficiency. -->
**"Wages"**, wherever used in this Manual in relation to the computation of gratuity, leave encashment or notice pay, means basic salary together with dearness allowance, and does **not** include house rent allowance, conveyance allowance, overtime, bonus, commission, or any other allowance by whatever name called. Where a provision of this Manual refers to "wages" without qualification, this definition applies.

---
clause_id: MER-IN-LONGSERVICE-AWARD
lineage_id: MER-IN-LONGSERVICE
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 6.5
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: india-national
corpus_requirement: R-19
---
<!-- R-19 synonym spread (probe P-33, failure mode FM-D4). The same benefit is
     named four ways across the corpus. All four phrasings must retrieve this. -->
An employee who completes ten (10) years of continuous service receives a **long service award** equal to one month's wages, and a further award of the same amount on completion of each subsequent period of five years. This award is separate from and additional to gratuity, and is not affected by the statutory gratuity ceiling. It is referred to elsewhere in Company communications as the *loyalty payment*, the *continuity recognition*, or the *service milestone grant*; these are the same benefit under this clause.

---
clause_id: MER-IN-CONFIRMATION
lineage_id: MER-IN-CONFIRMATION
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 3.5
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: india-national
corpus_requirement: R-26-filler
---
On satisfactory completion of probation an employee is confirmed in writing by the reporting manager, countersigned by Human Resources. Confirmation takes effect from the date stated in the confirmation letter. A confirmed employee becomes eligible for the Company's medical insurance scheme, the annual performance bonus, and the education assistance scheme, in each case from the effective date of confirmation.

---
clause_id: MER-IN-WORKING-HOURS
lineage_id: MER-IN-WORKING-HOURS
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 7.1
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: india-national
corpus_requirement: R-26-filler
---
The standard working week is forty-five (45) hours, worked over five days from Monday to Friday. Core hours during which an employee is expected to be available are 11:00 to 16:00. An employee required to work on a weekly holiday is entitled to compensatory time off, to be availed within thirty days.

---
clause_id: MER-IN-GRIEVANCE
lineage_id: MER-IN-GRIEVANCE
country: India
doc_type: policy
source_doc: Meridian India HR Policy Manual
section: 11.2
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: india-national
corpus_requirement: R-26-filler
---
An employee who wishes to raise a grievance shall do so in writing to their reporting manager in the first instance. Where the grievance concerns the reporting manager, or remains unresolved after fifteen working days, it may be escalated to the Head of Human Resources. A grievance concerning harassment is dealt with under the separate procedure in Chapter 12 and not under this clause.
