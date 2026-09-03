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
