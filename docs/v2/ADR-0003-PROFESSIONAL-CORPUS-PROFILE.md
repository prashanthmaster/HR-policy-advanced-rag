# ADR-0003: Use a bounded professional corpus, not a toy or volume theatre

- **Status:** accepted
- **Date:** 2026-09-06
- **Decision owner:** Prashanth

## Context

Phase 2A proved that one reviewed statutory extract and one synthetic company
policy could be admitted through a fail-closed manifest. That was an appropriate
seed but not sufficient evidence for professional ingestion or retrieval. The
legacy `corpus.zip` contains only the same eight Markdown files already present
in `corpus/`; all are quarantined or deferred after the legal/source audit.

Raw document count is not a quality measure. A large collection of duplicated,
uncited, or unverifiable text would make retrieval harder without demonstrating
professional engineering. Conversely, two clean Markdown files cannot expose
format, version, jurisdiction, policy-hierarchy, and applicability failures.

## Decision

The portfolio corpus is bounded to India and UAE mainland, with three question
families: gratuity/end-of-service, notice, and annual leave. `GLOBAL` records
provide policy hierarchy and answering procedure but do not create a third legal
jurisdiction.

The Phase 2B acceptance profile requires at least:

- 30 serving source records;
- 10 statutory-tier records, each distinguished as raw law, official guidance,
  subordinate law, or a project-authored reviewed extract;
- 20 conspicuously synthetic company policy, procedure, or FAQ records;
- 3 locally verified raw official PDFs;
- 8 explicit supersession edges;
- 10 isolated adversarial fixtures;
- two or more serving records for every India/UAE topic pair;
- zero unrecorded Markdown, PDF, DOCX, or HTML files under inventory roots.

The current generation exceeds those minima with 33 serving records, four raw
India PDFs, 188 locally verified official pages, 22 synthetic company records,
eight lineage edges, and ten adversarial fixtures.

Official source acquisition is evidence-bearing. A successfully acquired binary
is retained with its exact byte hash and independently observed page/size profile.
An endpoint that blocks acquisition remains `REMOTE_ONLY`; the repository records
the failure and uses a clearly labelled reviewed extract only where the supported
scope is known. Commercial commentary cannot silently replace an unavailable
official artifact.

The synthetic layer is not volume filler. It supplies policy hierarchy,
historical/current pairs, grandfathering, changes in notice bands and leave
carry-forward, different wage concepts, clarification requirements, deterministic
calculation inputs, and employee-language FAQs. Every serving synthetic text is
labelled `SYNTHETIC DOCUMENT — NOT A REAL COMPANY POLICY`.

## Integrity model

Manifest schema version 2 records title, document version, media type, source
kind, publication and effective dates, review date, and supersession links.
`REVIEWED_EXTRACT` is deliberately separate from `PRIMARY_LAW`: a curated
Markdown summary may retain statutory precedence for the bounded demo while its
provenance still makes clear that it is not the underlying legal instrument.
Validation rejects:

- unapproved domains for serving statutory sources;
- source-kind/tier contradictions;
- invalid date ranges, unknown predecessors, cross-jurisdiction lineage, and
  lineage cycles;
- media-type/extension mismatches;
- serving synthetic binary documents until Phase 3 can inspect their content;
- missing review metadata and synthetic text without both warning markers.

`scripts/build_corpus_manifest.py` deterministically rebuilds the manifest and
all content hashes. CI checks that the committed manifest is exactly reproducible.

## Consequences

- Phase 3 will be designed against actual 116-page, 38-page, 29-page, and
  five-page PDFs plus structured policy documents, not only tiny Markdown.
- UAE raw-binary ingestion cannot yet be claimed; the blocked official endpoints
  remain a visible limitation.
- Corpus scale is sufficient to exercise retrieval, but no retrieval-quality
  claim follows until chunks and known-relevant-query evaluations exist.
- The project remains a portfolio system using industry-grade controls, not
  production legal software. `production_legal_reviewed` stays false.
