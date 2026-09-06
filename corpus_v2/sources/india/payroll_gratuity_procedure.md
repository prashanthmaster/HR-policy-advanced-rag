# Meridian India — payroll gratuity calculation procedure

> **SYNTHETIC DOCUMENT — NOT A REAL COMPANY POLICY.**
> Meridian Global Services is fictional. This document exists only for the HR
> RAG portfolio demonstration and must never be presented as an actual employer
> policy or as legal advice.

## Inputs

Payroll records the employing entity, employee category, contract type, service
start and termination dates, termination reason, last-drawn wage components, and
currency. An incomplete record is returned to HR; zero is not used for a missing
wage component.

## Decision sequence

First determine statutory eligibility and any exception to the ordinary qualifying
period. Next determine reckonable service, including the treatment of a part-year.
Then determine the governing wage definition for the event date. Only after those
steps may the deterministic calculator apply the statutory rate and any notified
ceiling.

The calculation output records every input, intermediate value, rounding rule,
formula version, and supporting clause ID. A language model may explain this record
but may not replace or silently modify its arithmetic.

## Review

Death, disablement, forfeiture, disputed service, transferred employment, and
fixed-term cases receive a second-person review. A result is not released when the
approved corpus lacks a required notification or ceiling.
