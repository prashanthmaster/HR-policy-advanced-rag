# UAE — DIFC Statutory Employment Law (Tier 1: real public statutory sources)

Primary source: **DIFC Employment Law, DIFC Law No. 2 of 2019** (as amended), governing employment in the Dubai International Financial Centre. The DIFC is a financial free zone with its own employment regime, **separate from and not subordinate to** UAE mainland Federal Decree-Law No. 33 of 2021. An employee of a DIFC-registered entity is governed by this law, not the mainland law in `uae_law.md`.

**Article-number note.** Article 62 is cited for notice periods on the authority of the sources consulted. Article numbers for the leave and workplace-savings provisions were **not verified** and are therefore omitted rather than guessed; the provisions themselves are corroborated by two independent sources. Verify against the official DIFC legal database before any of these are quoted as article-level citations.

---
clause_id: DIFC-L2-2019-NOTICE
country: UAE
jurisdiction_scope: uae-difc
doc_type: law
source_act: DIFC Employment Law, DIFC Law No. 2 of 2019
section: Article 62
effective_date: 2019-08-28
revision_date: 2019-08-28
version: current
temporal_applicability: POINT_IN_TIME
normative: true
lineage_id: DIFC-NOTICE
source_url: https://www.difc.com/business/laws-and-regulations/legal-database/difc-laws/employment-law-difc-law-no-2-of-2019
---
The minimum period of written notice required to terminate an employee's employment is determined by the employee's period of continuous employment: (a) less than three (3) months — seven (7) days; (b) three (3) months or more but less than five (5) years — thirty (30) days; (c) five (5) years or more — ninety (90) days. These are statutory minimums which rise with length of service, in contrast to the mainland regime, under which the contractual notice period is fixed within a 30-to-90-day band irrespective of service length.

---
clause_id: DIFC-L2-2019-LEAVE
country: UAE
jurisdiction_scope: uae-difc
doc_type: law
source_act: DIFC Employment Law, DIFC Law No. 2 of 2019
section: (article number unverified)
effective_date: 2019-08-28
revision_date: 2019-08-28
version: current
temporal_applicability: SEGMENTED_ACCRUAL
normative: true
lineage_id: DIFC-LEAVE
source_url: https://www.difc.com/business/laws-and-regulations/legal-database/difc-laws/employment-law-difc-law-no-2-of-2019
---
An employee who has completed ninety (90) days of continuous employment is entitled to a minimum of twenty (20) **working** days of paid annual leave per year, accruing proportionately. Carry-forward is limited to five (5) days into the following year. **Note the unit of measurement:** DIFC counts annual leave in *working* days, whereas UAE mainland (Federal Decree-Law 33/2021, Article 29) counts thirty (30) *calendar* days. The two entitlements are not directly comparable by number alone.

---
clause_id: DIFC-L2-2019-DEWS
country: UAE
jurisdiction_scope: uae-difc
doc_type: law
source_act: DIFC Employment Law, DIFC Law No. 2 of 2019 — DIFC Employee Workplace Savings (DEWS)
section: (article number unverified)
effective_date: 2020-02-01
revision_date: 2020-02-01
version: current
temporal_applicability: SEGMENTED_ACCRUAL
normative: true
lineage_id: DIFC-EOSB
supersedes: DIFC-EOSB-LEGACY-GRATUITY
source_url: https://www.difc.com/business/laws-and-regulations/legal-database/difc-laws/employment-law-difc-law-no-2-of-2019
---
With effect from **1 February 2020**, the end-of-service gratuity regime for DIFC employees was replaced by a defined-contribution workplace savings scheme. The employer makes mandatory monthly contributions to the DIFC Employee Workplace Savings plan (or a qualifying alternative) at **5.83% of the employee's basic salary for the first five years of service, and 8.33% of basic salary for each year thereafter**. The employee's entitlement on termination is the accumulated value of the plan, not a lump sum computed from final salary.

---
clause_id: DIFC-EOSB-LEGACY-GRATUITY
country: UAE
jurisdiction_scope: uae-difc
doc_type: law
source_act: DIFC Employment Law — transitional treatment of pre-DEWS service
section: (article number unverified)
effective_date: 2019-08-28
revision_date: 2020-02-01
version: applies to service accrued before 2020-02-01 only
temporal_applicability: SEGMENTED_ACCRUAL
normative: true
lineage_id: DIFC-EOSB
superseded_by: DIFC-L2-2019-DEWS
source_url: https://www.difc.com/business/laws-and-regulations/legal-database/difc-laws/employment-law-difc-law-no-2-of-2019
---
Service accrued **before 1 February 2020** is not absorbed into the workplace savings scheme. It remains payable on termination as legacy end-of-service gratuity, computed on the pre-DEWS basis of twenty-one (21) days' basic salary for each of the first five years of service and thirty (30) days' basic salary for each year thereafter, by reference to the salary applicable at the transition. An employee whose service spans 1 February 2020 therefore receives **both**: legacy gratuity for the earlier segment and the accumulated DEWS value for the later segment.

---
clause_id: DIFC-L2-2019-PROBATION
country: UAE
jurisdiction_scope: uae-difc
doc_type: law
source_act: DIFC Employment Law, DIFC Law No. 2 of 2019
section: (article number unverified)
effective_date: 2019-08-28
revision_date: 2019-08-28
version: current
temporal_applicability: POINT_IN_TIME
normative: true
lineage_id: DIFC-PROBATION
source_url: https://www.difc.com/business/laws-and-regulations/legal-database/difc-laws/employment-law-difc-law-no-2-of-2019
---
The maximum probation period is six (6) months, or half the term of a fixed-term contract of less than six months' duration. This aligns with the mainland maximum under Federal Decree-Law 33/2021 Article 9 — one of the few points on which the two regimes agree, which makes probation a poor discriminator of jurisdiction and notice/gratuity/leave good ones.

---
## Why this file exists

The DIFC regime is a **real, verifiable divergence inside a single country** and is materially more useful to this project than a synthetic free-zone annexe would have been:

1. **The DEWS transition is a genuine statutory straddle.** An employee whose service spans 1 February 2020 splits into two segments computed on entirely different bases — legacy gratuity for the earlier, accumulated contributions for the later. This is a real `SEGMENTED_ACCRUAL` case in actual law.
2. **It contrasts directly with the India gratuity ceiling**, which is `POINT_IN_TIME` and must *not* be split. Two real straddle cases, opposite correct behaviours, both verifiable — an interviewer can check both.
3. **The leave provision is a unit trap.** "20" (working days, DIFC) versus "30" (calendar days, mainland) for the same words "annual leave" in the same country. Comparing the numbers without the units gives the wrong answer.
4. **Probation is deliberately identical across the two regimes**, so it cannot be used to infer which regime applies — the system must route on the employing entity, not on the substance of the answer.

**Scope note.** This is a bounded slice covering notice, end-of-service, leave quantum and probation only. Other DIFC provisions — including its parental leave provisions — are deliberately **out of scope** and must not be added: see `docs/DELIBERATE_DEFECTS.md` D-4, whose fixture depends on paternity leave being absent from the entire corpus.
