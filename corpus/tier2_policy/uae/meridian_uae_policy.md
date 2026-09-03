# Meridian Global Services FZ-LLC (United Arab Emirates) — HR Policy Manual

> ⚠️ **SYNTHETIC DOCUMENT — NOT A REAL COMPANY POLICY.**
> Meridian Global Services is a fictional entity. This chapter exists to exercise a retrieval system against realistic policy structure and must never be represented as a real HR policy or as legal guidance. Real UAE statutory law used by this project is in `corpus/tier1_law/uae/uae_law.md`, separately sourced and cited.

**Build status:** partial. Built incrementally against `docs/CORPUS_REQUIREMENTS.md`. Currently contains T-1.3 version-pair structures. Conflict and retrieval-mechanic structures follow in T-1.4 → T-1.5; connective prose in T-1.6.

---
clause_id: MER-AE-EOS-TOPUP-V1
lineage_id: MER-AE-EOS-TOPUP
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual
section: 6.3
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: GRANDFATHERED
superseded_by: MER-AE-EOS-TOPUP-V2
normative: true
jurisdiction_scope: uae-mainland
corpus_requirement: R-02
---
In addition to the end-of-service gratuity payable under the applicable labour law, an employee who completes three or more years of continuous service receives a Company end-of-service supplement of seven (7) days' basic wage for each completed year of service.

---
clause_id: MER-AE-EOS-TOPUP-V2
lineage_id: MER-AE-EOS-TOPUP
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual
section: 6.3
effective_date: 2025-01-01
revision_date: 2024-11-08
version: v2
temporal_applicability: GRANDFATHERED
cohort_rule: service_commenced_before(2025-01-01)
supersedes: MER-AE-EOS-TOPUP-V1
normative: true
jurisdiction_scope: uae-mainland
corpus_requirement: R-02
---
<!-- R-02 grandfathered amendment (probe P-06, failure mode FM-A4). BOTH versions
     are simultaneously current, for different populations. The cohort test is
     the joining date, which a query will usually not supply — which is what
     makes P-06 a MUST_CLARIFY rather than a MUST_ANSWER. -->
The Company end-of-service supplement described in clause 6.3 remains available to employees whose continuous service commenced **before 1 January 2025**, on the terms previously applicable. An employee whose continuous service commences **on or after 1 January 2025** is entitled to the statutory end-of-service gratuity only, and no Company supplement is payable.

---
clause_id: MER-AE-NOTICE-V2
lineage_id: MER-AE-NOTICE
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual
section: 4.1
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v2 (currently in force)
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: uae-mainland
corpus_requirement: R-03
---
An employee in any grade who wishes to resign shall give the Company thirty (30) days' written notice. The Company shall give the same period where it terminates the contract for a legitimate reason other than a ground permitting termination without notice.

---
clause_id: MER-AE-NOTICE-V3-PENDING
lineage_id: MER-AE-NOTICE
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual
section: 4.1
effective_date: 2027-01-01
revision_date: 2026-08-15
version: v3 (NOT YET IN FORCE)
temporal_applicability: POINT_IN_TIME
supersedes: MER-AE-NOTICE-V2
normative: true
jurisdiction_scope: uae-mainland
corpus_requirement: R-03
---
<!-- R-03 future-dated amendment (probe P-05, failure mode FM-A3). This is the
     NEWEST document in the lineage and is NOT YET IN FORCE. Naive semantic
     retrieval prefers it precisely because it is newest, and answering from it
     tells an employee a rule that does not yet govern them. Correct behaviour
     is to answer from V2 and FLAG this as pending with its effective date.
     This is the same class of error as answering from a superseded clause,
     pointed the other way in time. -->
With effect from **1 January 2027**, an employee in Grade M1 or above who wishes to resign shall give the Company sixty (60) days' written notice. The notice period for all other grades is unchanged at thirty (30) days. Published 15 August 2026.

---
clause_id: MER-AE-PROBATION-V1
lineage_id: MER-AE-PROBATION
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual
section: 3.4
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
superseded_by: MER-AE-PROBATION-V2
normative: true
jurisdiction_scope: uae-mainland
corpus_requirement: R-05
---
<!-- R-05 SILENT supersession (probe P-07, failure mode FM-A5). Note that this
     clause's TEXT contains no indication whatever that it has been superseded —
     no "replaced by", no strikethrough, no marker. It simply sits in the folder
     looking current. Supersession is recoverable ONLY from lineage metadata and
     effective dates. Do not add a marker to the text; that defuses the probe. -->
A new employee is engaged on probation for a period of six (6) months from the date of commencing work. The Company may terminate the engagement during probation on fourteen (14) days' written notice.

---
clause_id: MER-AE-PROBATION-V2
lineage_id: MER-AE-PROBATION
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual
section: 3.4
effective_date: 2024-04-01
revision_date: 2024-03-19
version: v2
temporal_applicability: POINT_IN_TIME
supersedes: MER-AE-PROBATION-V1
normative: true
jurisdiction_scope: uae-mainland
corpus_requirement: R-05
---
A new employee is engaged on probation for a period of three (3) months from the date of commencing work. The Company may terminate the engagement during probation on fourteen (14) days' written notice.

---
clause_id: MER-AE-S72-V1-REMOTEWORK
lineage_id: MER-AE-REMOTEWORK
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual
section: 7.2
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: uae-mainland
corpus_requirement: R-08
---
<!-- R-08 clause-number reuse (probe P-10, failure mode FM-A8). In manual v1,
     section "7.2" is Remote Working. In manual v2 the chapter was reorganised
     and "7.2" became Business Travel, with remote working moved to 7.5. A query
     asking "what does clause 7.2 say" is genuinely ambiguous across versions
     and must never be resolved by matching the number alone. -->
**7.2 Remote Working.** An employee may work remotely for up to two days in each calendar week with the written agreement of their line manager.

---
clause_id: MER-AE-S72-V2-BUSINESSTRAVEL
lineage_id: MER-AE-BUSINESSTRAVEL
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual
section: 7.2
effective_date: 2025-06-01
revision_date: 2025-05-22
version: v2
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: uae-mainland
corpus_requirement: R-08
note: section number 7.2 reused; unrelated in substance to MER-AE-S72-V1-REMOTEWORK
---
**7.2 Business Travel.** An employee travelling on Company business is reimbursed actual and reasonable expenses on production of receipts, subject to the per-diem limits set out in Schedule 3.

---
clause_id: MER-AE-S75-REMOTEWORK
lineage_id: MER-AE-REMOTEWORK
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual
section: 7.5
effective_date: 2025-06-01
revision_date: 2025-05-22
version: v2
temporal_applicability: POINT_IN_TIME
supersedes: MER-AE-S72-V1-REMOTEWORK
normative: true
jurisdiction_scope: uae-mainland
corpus_requirement: R-08
---
**7.5 Remote Working.** An employee may work remotely for up to two days in each calendar week with the written agreement of their line manager. (Renumbered from 7.2 on reorganisation of Chapter 7; substance unchanged.)

---
clause_id: MER-AE-DIFC-ANNEXE-SCOPE
lineage_id: MER-AE-DIFC-SCOPE
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual — DIFC Annexe
section: Annexe A.1
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: uae-difc
corpus_requirement: R-12
---
This Annexe applies to employees of **Meridian Global Services (DIFC) Limited**, registered in the Dubai International Financial Centre. Those employees are governed by the DIFC Employment Law, DIFC Law No. 2 of 2019, and **not** by UAE Federal Decree-Law No. 33 of 2021. Where this Annexe is silent, the main UAE chapter applies only to the extent it is not inconsistent with DIFC law. An employee's applicable regime is determined by the Meridian entity with which they hold their contract of employment, not by the office building in which they work — an employee of the mainland entity seconded to the DIFC office remains subject to the mainland regime, and the converse also holds.

---
clause_id: MER-AE-DIFC-NOTICE
lineage_id: MER-AE-DIFC-NOTICE
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual — DIFC Annexe
section: Annexe A.4
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: uae-difc
corpus_requirement: R-13
references: [DIFC-L2-2019-NOTICE]
---
<!-- R-13 near-identical clause, different numbers, SAME COUNTRY (probe P-17,
     failure mode FM-B5/FM-B6). Compare with MER-AE-NOTICE-V2 in the main
     chapter: near-identical wording, materially different entitlement at
     5+ years (90 days here, 30 there). Country filtering alone does NOT
     separate these — the filter must be on jurisdiction_scope. This is a
     harder version of the cross-country contamination case. -->
An employee who wishes to resign, or whose employment the Company terminates, is entitled to and shall give written notice in accordance with the statutory minimum periods under the DIFC Employment Law, namely: seven (7) days where continuous employment is less than three months; thirty (30) days where continuous employment is three months or more but less than five years; and **ninety (90) days where continuous employment is five years or more**. The Company does not apply a shorter period.

---
clause_id: MER-AE-DIFC-EOSB
lineage_id: MER-AE-DIFC-EOSB
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual — DIFC Annexe
section: Annexe A.6
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: SEGMENTED_ACCRUAL
normative: true
jurisdiction_scope: uae-difc
references: [DIFC-L2-2019-DEWS, DIFC-EOSB-LEGACY-GRATUITY]
---
The Company enrols every employee of the DIFC entity in the DIFC Employee Workplace Savings plan and makes the mandatory monthly contributions. An employee whose continuous service commenced **before 1 February 2020** additionally retains an entitlement to legacy end-of-service gratuity in respect of the service accrued up to that date, computed on the pre-transition basis. Such an employee's total end-of-service entitlement is therefore the sum of two separately computed components covering two consecutive periods of the same continuous service. The Company end-of-service supplement described in clause 6.3 of the main chapter does **not** apply to employees of the DIFC entity.

---
clause_id: MER-AE-DIFC-LEAVE
lineage_id: MER-AE-DIFC-LEAVE
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual — DIFC Annexe
section: Annexe A.5
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: SEGMENTED_ACCRUAL
normative: true
jurisdiction_scope: uae-difc
references: [DIFC-L2-2019-LEAVE]
---
An employee who has completed ninety (90) days of continuous employment accrues twenty-five (25) **working** days of paid annual leave per year, which exceeds the DIFC statutory minimum of twenty working days. Employees should note that this entitlement is expressed in *working* days, whereas the entitlement of employees of the mainland entity is expressed in *calendar* days; the two figures are not comparable without converting to a common basis.

---
clause_id: MER-AE-HOUSING-TABLE
lineage_id: MER-AE-HOUSING
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual — Schedule 2
section: Schedule 2
effective_date: 2024-01-01
revision_date: 2023-12-04
version: v2
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: uae-mainland
chunk_stream: table
corpus_requirement: R-16
---
<!-- R-16 two-dimensional slab table (probe P-30, failure mode FM-D1). Serialised
     row-wise as text per the no-vision decision. This is the concrete
     justification for hybrid retrieval: embeddings do not reliably distinguish
     "AED 8,000" from "AED 9,500" in near-identical rows; the BM25 leg plus row
     serialisation is what lands the correct cell. -->
**Schedule 2 — Monthly housing allowance, by grade and completed years of service (AED).**

- Grade A1–A3, under 3 years of service: 4,000 per month.
- Grade A1–A3, 3 to 5 years of service: 4,500 per month.
- Grade A1–A3, over 5 years of service: 5,000 per month.
- Grade M1, under 3 years of service: 6,500 per month.
- Grade M1, 3 to 5 years of service: 7,200 per month.
- Grade M1, over 5 years of service: 8,000 per month.
- Grade M2, under 3 years of service: 8,500 per month.
- Grade M2, 3 to 5 years of service: 9,500 per month.
- Grade M2, over 5 years of service: 10,500 per month.
- Grade M3, under 3 years of service: 11,000 per month.
- Grade M3, 3 to 5 years of service: 12,500 per month.
- Grade M3, over 5 years of service: 14,000 per month.
- Grade D1 and above, any length of service: 18,000 per month.

The allowance is paid monthly with salary and is not part of basic wage for the purpose of computing end-of-service entitlements (see clause 2.11).

---
clause_id: MER-AE-DEFN-BASICWAGE
lineage_id: MER-AE-DEFN-BASICWAGE
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual — Chapter 2, Definitions
section: 2.11
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: uae-mainland
corpus_requirement: R-22
---
<!-- R-22 scattered operands (probe P-36, failure mode FM-D7). A UAE end-of-
     service settlement needs THREE separate chunks: this wage-base definition,
     the statutory 21/30-day rate bands, and the two-year cap. Retrieving two of
     three yields a confident wrong number rather than a visible gap — which is
     why partial retrieval must refuse rather than part-compute. -->
**"Basic wage"** means the wage stated in the employment contract as basic salary, excluding housing allowance, transport allowance, education allowance, mobile allowance, and any other allowance or benefit in kind. End-of-service entitlements, and payment in lieu of notice, are computed on basic wage and not on total remuneration. An employee's basic wage is typically between 50% and 60% of total monthly remuneration.

---
clause_id: MER-AE-TRAVEL-V1
lineage_id: MER-AE-TRAVEL
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual
section: 9.3
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
superseded_by: MER-AE-TRAVEL-V2
normative: true
jurisdiction_scope: uae-mainland
corpus_requirement: R-21
---
<!-- R-21 near-duplicate version pair (probe P-35, failure mode FM-D6). This and
     V2 differ by one word ("economy" -> "premium economy") and one numeral.
     Both score almost identically on any similarity measure and flood the top-k
     together, crowding out the clause that actually answers a broader travel
     query. Lineage dedup before rerank is the fix. -->
An employee travelling on Company business within the GCC travels in economy class. An employee travelling on Company business outside the GCC, where the scheduled flight time exceeds six (6) hours, travels in economy class and is entitled to one additional rest day on arrival before commencing scheduled work.

---
clause_id: MER-AE-TRAVEL-V2
lineage_id: MER-AE-TRAVEL
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual
section: 9.3
effective_date: 2025-01-01
revision_date: 2024-12-10
version: v2
temporal_applicability: POINT_IN_TIME
supersedes: MER-AE-TRAVEL-V1
normative: true
jurisdiction_scope: uae-mainland
corpus_requirement: R-21
---
An employee travelling on Company business within the GCC travels in economy class. An employee travelling on Company business outside the GCC, where the scheduled flight time exceeds seven (7) hours, travels in premium economy class and is entitled to one additional rest day on arrival before commencing scheduled work.

---
clause_id: MER-AE-MEDICAL
lineage_id: MER-AE-MEDICAL
country: UAE
doc_type: policy
source_doc: Meridian UAE HR Policy Manual
section: 10.1
effective_date: 2023-01-01
revision_date: 2023-01-01
version: v1
temporal_applicability: POINT_IN_TIME
normative: true
jurisdiction_scope: uae-mainland
corpus_requirement: R-26-filler
---
The Company provides medical insurance cover for every employee as required by law, and extends cover to a spouse and up to three dependent children at Company cost for employees in Grade M1 and above. Employees below Grade M1 may enrol dependants at their own cost through payroll deduction during the annual enrolment window each November.
