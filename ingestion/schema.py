"""
Extended chunk schema for the HR-Policy RAG corpus.

This is the single source of truth for what a "chunk" is allowed to carry.
eval/coverage_audit.py checks the raw markdown against a hand-rolled copy of
these field names; this module is the real, importable, validated version
used by the ingestion pipeline. If you add a field here, also add it to
coverage_audit.py's REQUIRED_FIELDS / PIPELINE_FIELDS lists, or the two will
drift again the way the Tier-1 files did in Phase 1.

Design notes (why these fields exist, not just what they are):

- effective_date / revision_date / indexed_at are the "three clocks" finding
  from docs/FAILURE_MODES.md: the legal fact, the Drive bookkeeping fact, and
  the pipeline bookkeeping fact are three different dates and must never be
  conflated. Retrieval-time filtering happens on effective_date against an
  as-of date supplied by the caller, never on revision_date or indexed_at.
- temporal_applicability is the other Phase-0 finding: a clause's version
  history isn't always "old vs new, pick new" -- it can require splitting a
  period of service across a boundary (SEGMENTED_ACCRUAL), holding two
  versions simultaneously current for different cohorts (GRANDFATHERED), or
  letting the employee elect the more favourable of two (ELECTIVE). Retrieval
  and generation both need to know which regime a clause is in before they
  can decide whether "give me the current answer" is even a well-formed
  question for that clause.
- normative distinguishes a clause employees can rely on from one that only
  illustrates a computation (D-2's decoy illustration) or is already flagged
  historical (a SUPERSEDED clause). A generator must never cite a
  normative:false clause as the basis for an entitlement.
- lineage_id groups every version of "the same rule" across time so that
  supersession/grandfathering/segmentation can be resolved by looking up all
  chunks sharing a lineage_id, rather than by string-matching clause_ids.
"""

from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class TemporalApplicability(str, Enum):
    """How a clause's effective_date interacts with a case whose relevant
    period straddles the clause's boundary. See docs/FAILURE_MODES.md,
    Part 1, Finding 1."""

    POINT_IN_TIME = "POINT_IN_TIME"
    SEGMENTED_ACCRUAL = "SEGMENTED_ACCRUAL"
    GRANDFATHERED = "GRANDFATHERED"
    ELECTIVE = "ELECTIVE"


class DocType(str, Enum):
    LAW = "law"
    POLICY = "policy"


class ChunkStream(str, Enum):
    """Most clauses are prose. A few (R-16, the UAE housing-allowance slab
    table) are structured tables that must be serialized to text a different
    way -- row-by-row with the governing dimensions repeated on every row --
    rather than chunked as a paragraph. See T-2.4."""

    PROSE = "prose"
    TABLE = "table"


class ChunkMetadata(BaseModel):
    """The metadata block that precedes every clause body in the corpus
    markdown files (between the `---` fences). One instance of this class
    corresponds to one retrieval chunk (pre-splitting; T-2.3's clause-aware
    chunker may still split a long clause body into multiple *pieces* that
    all share this same metadata, but it must never split a clause's
    operative provisos from the metadata that scopes them -- see D-1 and
    MER-IN-GRATUITY-FORFEITURE in docs/DELIBERATE_DEFECTS.md / R-17)."""

    # extra="allow": the corpus grows metadata fields faster than this
    # module gets updated (that is exactly what happened to the Tier-1 law
    # files in Phase 1 -- see the schema-drift entry in the Errors section
    # of project memory). Known fields are validated and typed below;
    # anything else (deliberate_defect, corpus_requirement, and whatever
    # the next phase invents) survives in `model_extra` instead of raising,
    # so ingestion never hard-fails on a field it doesn't know about yet --
    # it only hard-fails on a REQUIRED field being wrong or missing.
    model_config = {"extra": "allow"}

    # --- identity -----------------------------------------------------
    clause_id: str
    country: str
    doc_type: DocType
    source_doc: Optional[str] = Field(
        default=None, description="Tier-2 policy document name (Tier-1 law uses source_act instead)"
    )
    deliberate_defect: Optional[str] = Field(
        default=None, description="D-n manifest id, when this clause is a deliberate fixture (docs/DELIBERATE_DEFECTS.md)"
    )
    corpus_requirement: Optional[str] = Field(
        default=None, description="R-nn id this clause exists to satisfy (docs/CORPUS_REQUIREMENTS.md)"
    )

    # --- the three clocks ----------------------------------------------
    effective_date: Optional[dt.date] = Field(
        default=None,
        description=(
            "The legal/policy fact: the date from which this clause's rule "
            "governs. None only for the deliberately UNRESOLVED case "
            "(R-09, MER-IN-RELOCATION) where the corpus itself is silent -- "
            "the pipeline must preserve that silence, not default it to "
            "indexed_at."
        ),
    )
    effective_date_unresolved: bool = Field(
        default=False,
        description="True iff effective_date is None on purpose (R-09), as "
        "opposed to missing because nobody filled it in.",
    )
    revision_date: Optional[dt.date] = Field(
        default=None,
        description="Drive modifiedTime equivalent -- when the source "
        "document was last touched. Populated by the ingestion pipeline "
        "from Drive metadata, not authored in the markdown.",
    )
    indexed_at: Optional[dt.datetime] = Field(
        default=None,
        description="Pipeline bookkeeping -- when this chunk was written "
        "into the index. Populated by the pipeline, not authored.",
    )

    # --- versioning / lineage -------------------------------------------
    version: Optional[str] = None
    lineage_id: Optional[str] = Field(
        default=None,
        description="Groups every version of 'the same rule' across time. "
        "Required on every clause once Phase 1's schema-drift fix landed.",
    )
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    temporal_applicability: Optional[TemporalApplicability] = None

    # --- normativity / cross-refs ----------------------------------------
    normative: bool = Field(
        default=True,
        description="False for illustrations (D-2), decoys, or clauses "
        "explicitly marked historical/superseded in the source text.",
    )
    references: list[str] = Field(
        default_factory=list,
        description="Other clause_ids this clause depends on/cites, e.g. "
        "'[IN-GRAT-S4-ELIG, IN-GRAT-S4-FORMULA]' in the source markdown.",
    )
    illustrates: Optional[str] = None

    @field_validator("references", mode="before")
    @classmethod
    def _parse_references(cls, v: object) -> object:
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                s = s[1:-1]
            if not s:
                return []
            return [part.strip() for part in s.split(",") if part.strip()]
        return v

    # --- scope / jurisdiction --------------------------------------------
    jurisdiction_scope: Optional[str] = None
    source_act: Optional[str] = None
    section: Optional[str] = None
    source_url: Optional[str] = None

    # --- retrieval mechanics ----------------------------------------------
    chunk_stream: ChunkStream = ChunkStream.PROSE

    @model_validator(mode="before")
    @classmethod
    def _handle_unresolved_effective_date(cls, data: object) -> object:
        # R-09 (MER-IN-RELOCATION) writes the literal token UNRESOLVED in
        # the markdown, on purpose, to represent a real drafting gap the
        # source document never closed. That must survive as
        # effective_date=None + effective_date_unresolved=True, not get
        # coerced into today's date or rejected as a parse error.
        if isinstance(data, dict):
            ed = data.get("effective_date")
            if isinstance(ed, str) and ed.strip().upper() == "UNRESOLVED":
                data = dict(data)
                data["effective_date"] = None
                data["effective_date_unresolved"] = True
        return data

    @field_validator("country")
    @classmethod
    def _country_known(cls, v: str) -> str:
        # GLOBAL is a real fourth value, not a typo: the Meridian preamble
        # (scope, governing-law silence D-5, amendment procedure) applies
        # across all three jurisdictions at once rather than to one of them,
        # and must not be forced into a false single-country home.
        allowed = {"India", "UAE", "Germany", "GLOBAL"}
        if v not in allowed:
            raise ValueError(f"country {v!r} not in {allowed} (Slot 4 scope is fixed to these three plus GLOBAL)")
        return v

    @model_validator(mode="after")
    def _effective_date_consistency(self) -> "ChunkMetadata":
        if self.effective_date is None and not self.effective_date_unresolved:
            raise ValueError(
                f"{self.clause_id}: effective_date is missing and "
                "effective_date_unresolved is not set -- either fill in the "
                "date or mark it deliberately unresolved (R-09 pattern)"
            )
        if self.effective_date is not None and self.effective_date_unresolved:
            raise ValueError(
                f"{self.clause_id}: has both effective_date and "
                "effective_date_unresolved=True -- pick one"
            )
        return self

    @model_validator(mode="after")
    def _temporal_applicability_required_for_law_and_versioned(self) -> "ChunkMetadata":
        # Every clause in the corpus was backfilled with temporal_applicability
        # in Phase 1 (the schema-drift fix). Ingestion should refuse to index
        # anything that regresses on that, since retrieval-time segmentation
        # logic (Phase 3+) depends on every chunk declaring its regime.
        if self.temporal_applicability is None:
            raise ValueError(
                f"{self.clause_id}: temporal_applicability is required on "
                "every chunk (see docs/FAILURE_MODES.md Finding 1)"
            )
        return self


class Chunk(BaseModel):
    """A metadata block plus its body text, exactly as extracted from one
    `---`-delimited section of a corpus markdown file."""

    model_config = {"extra": "forbid"}

    metadata: ChunkMetadata
    body: str
    source_file: str = Field(description="Repo-relative path this chunk was parsed from")
    order_in_file: int = Field(description="0-based position among clauses in source_file, for stable tie-breaking")

    @field_validator("body")
    @classmethod
    def _body_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("chunk body is empty")
        return v
