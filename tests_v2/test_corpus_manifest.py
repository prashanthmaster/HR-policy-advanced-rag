from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from hr_policy_rag.corpus import (
    CertificationLevel,
    CorpusIntegrityError,
    CorpusManifest,
    CorpusUse,
    ManifestSource,
    SourceKind,
    SourceMediaType,
    load_verified_corpus,
)
from hr_policy_rag.domain import NormativeTier

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPOSITORY_ROOT / "corpus_v2" / "manifest.json"
ACQUISITION_STATUS_PATH = REPOSITORY_ROOT / "corpus_v2" / "acquisition_status.json"
AS_OF_DATE = dt.date(2026, 9, 6)


def _sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    canonical_bytes = text.replace("\r\n", "\n").replace("\r", "\n").encode()
    return hashlib.sha256(canonical_bytes).hexdigest()


def _source(**overrides: object) -> ManifestSource:
    values: dict[str, object] = {
        "source_id": "india-gratuity-law",
        "title": "India gratuity law",
        "document_version": "2020",
        "relative_path": "corpus_v2/sources/india/gratuity_statutory_extract.md",
        "content_sha256": "a" * 64,
        "media_type": SourceMediaType.MARKDOWN,
        "source_kind": SourceKind.PRIMARY_LAW,
        "use": CorpusUse.SERVING,
        "jurisdiction": "India",
        "topics": ("gratuity",),
        "normative_tier": NormativeTier.STATUTORY,
        "synthetic": False,
        "certification_level": CertificationLevel.PRIMARY_SOURCE_CHECKED,
        "official_source_urls": ("https://www.labour.gov.in/example.pdf",),
        "approved_locators": ("Section 53",),
        "reason_codes": (),
        "published_on": dt.date(2020, 9, 29),
        "effective_from": dt.date(2025, 11, 21),
        "reviewed_on": AS_OF_DATE,
        "supersedes": (),
    }
    values.update(overrides)
    if values["normative_tier"] is NormativeTier.COMPANY_POLICY and "source_kind" not in overrides:
        values["source_kind"] = SourceKind.COMPANY_POLICY
    return ManifestSource.model_validate(values)


def test_committed_manifest_meets_phase_2b_portfolio_profile() -> None:
    verified = load_verified_corpus(MANIFEST_PATH, repository_root=REPOSITORY_ROOT)

    assert verified.manifest.schema_version == 2
    assert verified.manifest.active_jurisdictions == ("GLOBAL", "India", "UAE")
    assert verified.manifest.active_topics == ("gratuity", "notice", "leave")
    assert len(verified.serving_sources) >= 30
    assert sum(source.normative_tier is NormativeTier.STATUTORY for source in verified.serving_sources) >= 10
    assert sum(source.synthetic for source in verified.serving_sources) >= 20
    assert sum(source.media_type is SourceMediaType.PDF for source in verified.serving_sources) >= 3
    assert sum(len(source.supersedes) for source in verified.serving_sources) >= 8
    assert sum(source.use is CorpusUse.ADVERSARIAL_TEST for source in verified.manifest.sources) >= 10
    for jurisdiction in ("India", "UAE"):
        for topic in verified.manifest.active_topics:
            assert (
                sum(
                    source.jurisdiction == jurisdiction and topic in source.topics
                    for source in verified.serving_sources
                )
                >= 2
            )
    assert all(source.use is CorpusUse.SERVING for source in verified.serving_sources)
    assert not verified.manifest.production_legal_reviewed
    assert len(verified.corpus_sha256) == 64

    raw_law = next(source for source in verified.serving_sources if source.source_id == "in-coss-2020-raw")
    reviewed_extract = next(
        source for source in verified.serving_sources if source.source_id == "ae-labour-law-end-of-service-extract"
    )
    assert raw_law.source_kind is SourceKind.PRIMARY_LAW
    assert reviewed_extract.source_kind is SourceKind.REVIEWED_EXTRACT


def test_every_legacy_markdown_source_is_explicitly_non_serving() -> None:
    verified = load_verified_corpus(MANIFEST_PATH, repository_root=REPOSITORY_ROOT)
    recorded = {source.relative_path: source for source in verified.manifest.sources}
    legacy_paths = {path.relative_to(REPOSITORY_ROOT).as_posix() for path in (REPOSITORY_ROOT / "corpus").rglob("*.md")}

    assert legacy_paths <= recorded.keys()
    assert all(recorded[path].use is not CorpusUse.SERVING for path in legacy_paths)


def test_certified_legal_facts_exclude_the_v1_falsehood_and_record_scope_limit() -> None:
    verified = load_verified_corpus(MANIFEST_PATH, repository_root=REPOSITORY_ROOT)
    serving_text = "\n".join(
        (REPOSITORY_ROOT / source.relative_path).read_text(encoding="utf-8")
        for source in verified.serving_sources
        if source.media_type is SourceMediaType.MARKDOWN
    )

    assert "ordinary rule in the approved statutory material remains five years" in serving_text
    assert "21 November 2025" in serving_text
    assert "twenty-one days of basic wage" in serving_text
    assert "thirty calendar days" in serving_text
    assert "four years is sufficient" not in serving_text

    raw_sources = [source for source in verified.serving_sources if source.media_type is SourceMediaType.PDF]
    assert all((REPOSITORY_ROOT / source.relative_path).read_bytes().startswith(b"%PDF-") for source in raw_sources)


def test_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    source_path = tmp_path / "source.md"
    source_path.write_text("trusted\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest = CorpusManifest(
        schema_version=1,
        corpus_generation="test-generation",
        as_of_date=AS_OF_DATE,
        active_jurisdictions=("India",),
        active_topics=("gratuity",),
        production_legal_reviewed=False,
        inventory_roots=(),
        sources=(
            _source(
                relative_path="source.md",
                content_sha256="0" * 64,
            ),
        ),
    )
    manifest_path.write_text(json.dumps(manifest.model_dump(mode="json")), encoding="utf-8")

    with pytest.raises(CorpusIntegrityError, match="SOURCE_HASH_MISMATCH"):
        load_verified_corpus(manifest_path, repository_root=tmp_path)


def test_missing_source_fails_closed(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest = CorpusManifest(
        schema_version=1,
        corpus_generation="test-generation",
        as_of_date=AS_OF_DATE,
        active_jurisdictions=("India",),
        active_topics=("gratuity",),
        production_legal_reviewed=False,
        inventory_roots=(),
        sources=(_source(relative_path="missing.md"),),
    )
    manifest_path.write_text(json.dumps(manifest.model_dump(mode="json")), encoding="utf-8")

    with pytest.raises(CorpusIntegrityError, match="SOURCE_MISSING"):
        load_verified_corpus(manifest_path, repository_root=tmp_path)


def test_manifest_rejects_path_traversal_duplicate_ids_and_unsafe_statute() -> None:
    with pytest.raises(ValidationError, match="relative_path"):
        _source(relative_path="../outside.md")

    with pytest.raises(ValidationError, match="official source"):
        _source(official_source_urls=())

    with pytest.raises(ValidationError, match="primary-source certification"):
        _source(certification_level=CertificationLevel.NOT_REVIEWED)

    source = _source()
    with pytest.raises(ValidationError, match="source_id values must be unique"):
        CorpusManifest(
            schema_version=1,
            corpus_generation="test-generation",
            as_of_date=AS_OF_DATE,
            active_jurisdictions=("India",),
            active_topics=("gratuity",),
            production_legal_reviewed=False,
            inventory_roots=(),
            sources=(source, source),
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"topics": ("gratuity", "gratuity")}, "topics must not contain duplicates"),
        (
            {
                "use": CorpusUse.QUARANTINED,
                "certification_level": CertificationLevel.NOT_REVIEWED,
                "official_source_urls": (),
                "reason_codes": ("BAD", "BAD"),
            },
            "reason_codes must not contain duplicates",
        ),
        ({"reason_codes": ("SHOULD_NOT_BE_HERE",)}, "serving source cannot carry"),
        ({"synthetic": True}, "serving statutory source cannot be synthetic"),
        (
            {
                "normative_tier": NormativeTier.COMPANY_POLICY,
                "official_source_urls": (),
            },
            "must be explicitly synthetic",
        ),
        (
            {
                "normative_tier": NormativeTier.COMPANY_POLICY,
                "synthetic": True,
                "certification_level": CertificationLevel.NOT_REVIEWED,
                "official_source_urls": (),
            },
            "requires policy review",
        ),
    ],
)
def test_source_rejects_ambiguous_or_unsafe_certification(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        _source(**overrides)


def test_serving_sources_reject_unapproved_authority_domains_and_uninspectable_synthetic_binary() -> None:
    with pytest.raises(ValidationError, match="approved official domain"):
        _source(official_source_urls=("https://example.com/law.pdf",))

    with pytest.raises(ValidationError, match="approved locator"):
        _source(approved_locators=())

    with pytest.raises(ValidationError, match="synthetic binary"):
        _source(
            relative_path="policy.pdf",
            media_type=SourceMediaType.PDF,
            source_kind=SourceKind.COMPANY_POLICY,
            normative_tier=NormativeTier.COMPANY_POLICY,
            synthetic=True,
            certification_level=CertificationLevel.DEMO_POLICY_REVIEWED,
            official_source_urls=(),
        )

    with pytest.raises(ValidationError, match="statutory source_kind"):
        _source(source_kind=SourceKind.COMPANY_POLICY)

    with pytest.raises(ValidationError, match="company source_kind"):
        _source(
            source_kind=SourceKind.PRIMARY_LAW,
            normative_tier=NormativeTier.COMPANY_POLICY,
            synthetic=True,
            certification_level=CertificationLevel.DEMO_POLICY_REVIEWED,
            official_source_urls=(),
        )


def test_non_serving_source_requires_reason_and_cannot_leak_into_serving_set(tmp_path: Path) -> None:
    fixture_path = tmp_path / "false-rule.md"
    fixture_path.write_text("False rule for adversarial testing only.\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="reason code"):
        _source(
            source_id="false-rule",
            relative_path="false-rule.md",
            use=CorpusUse.ADVERSARIAL_TEST,
            certification_level=CertificationLevel.NOT_REVIEWED,
            official_source_urls=(),
        )

    fixture = _source(
        source_id="false-rule",
        relative_path="false-rule.md",
        content_sha256=_sha256(fixture_path),
        use=CorpusUse.ADVERSARIAL_TEST,
        certification_level=CertificationLevel.NOT_REVIEWED,
        official_source_urls=(),
        reason_codes=("INTENTIONALLY_FALSE",),
    )
    manifest = CorpusManifest(
        schema_version=1,
        corpus_generation="test-generation",
        as_of_date=AS_OF_DATE,
        active_jurisdictions=("India",),
        active_topics=("gratuity",),
        production_legal_reviewed=False,
        inventory_roots=(),
        sources=(fixture,),
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(mode="json")), encoding="utf-8")

    verified = load_verified_corpus(manifest_path, repository_root=tmp_path)
    assert verified.serving_sources == ()


def test_synthetic_serving_policy_requires_an_explicit_banner(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.md"
    policy_path.write_text("A plausible policy without a synthetic warning.\n", encoding="utf-8")
    policy = _source(
        source_id="fictional-policy",
        relative_path="policy.md",
        content_sha256=_sha256(policy_path),
        normative_tier=NormativeTier.COMPANY_POLICY,
        synthetic=True,
        certification_level=CertificationLevel.DEMO_POLICY_REVIEWED,
        official_source_urls=(),
    )
    manifest = CorpusManifest(
        schema_version=1,
        corpus_generation="test-generation",
        as_of_date=AS_OF_DATE,
        active_jurisdictions=("India",),
        active_topics=("gratuity",),
        production_legal_reviewed=False,
        inventory_roots=(),
        sources=(policy,),
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(mode="json")), encoding="utf-8")

    with pytest.raises(CorpusIntegrityError, match="SYNTHETIC_BANNER_MISSING"):
        load_verified_corpus(manifest_path, repository_root=tmp_path)


def test_manifest_scope_and_review_invariants() -> None:
    source = _source()
    with pytest.raises(ValidationError, match="active scope"):
        CorpusManifest(
            schema_version=1,
            corpus_generation="test-generation",
            as_of_date=AS_OF_DATE,
            active_jurisdictions=("UAE",),
            active_topics=("gratuity",),
            production_legal_reviewed=False,
            inventory_roots=(),
            sources=(source,),
        )
    with pytest.raises(ValidationError, match="active_jurisdictions values must be unique"):
        CorpusManifest(
            schema_version=1,
            corpus_generation="test-generation",
            as_of_date=AS_OF_DATE,
            active_jurisdictions=("India", "India"),
            active_topics=("gratuity",),
            production_legal_reviewed=False,
            inventory_roots=(),
            sources=(source,),
        )
    with pytest.raises(ValidationError, match="relative_path values must be unique"):
        CorpusManifest(
            schema_version=1,
            corpus_generation="test-generation",
            as_of_date=AS_OF_DATE,
            active_jurisdictions=("India",),
            active_topics=("gratuity",),
            production_legal_reviewed=False,
            inventory_roots=(),
            sources=(source, source.model_copy(update={"source_id": "another-source"})),
        )
    with pytest.raises(ValidationError, match="inside the active scope"):
        CorpusManifest(
            schema_version=1,
            corpus_generation="test-generation",
            as_of_date=AS_OF_DATE,
            active_jurisdictions=("India",),
            active_topics=("notice",),
            production_legal_reviewed=False,
            inventory_roots=(),
            sources=(source,),
        )
    with pytest.raises(ValidationError, match="legal review of every serving statute"):
        CorpusManifest(
            schema_version=1,
            corpus_generation="test-generation",
            as_of_date=AS_OF_DATE,
            active_jurisdictions=("India",),
            active_topics=("gratuity",),
            production_legal_reviewed=True,
            inventory_roots=(),
            sources=(source,),
        )


def test_inventory_rejects_missing_root_and_unaccounted_markdown(tmp_path: Path) -> None:
    source_path = tmp_path / "source.md"
    source_path.write_text("trusted\n", encoding="utf-8")
    source = _source(relative_path="source.md", content_sha256=_sha256(source_path))

    for inventory_root, expected_code in (
        ("missing", "INVENTORY_ROOT_MISSING"),
        ("inventory", "UNACCOUNTED_SOURCE"),
    ):
        if inventory_root == "inventory":
            inventory_path = tmp_path / inventory_root
            inventory_path.mkdir()
            (inventory_path / "unrecorded.md").write_text("unrecorded\n", encoding="utf-8")
        manifest = CorpusManifest(
            schema_version=1,
            corpus_generation="test-generation",
            as_of_date=AS_OF_DATE,
            active_jurisdictions=("India",),
            active_topics=("gratuity",),
            production_legal_reviewed=False,
            inventory_roots=(inventory_root,),
            sources=(source,),
        )
        manifest_path = tmp_path / f"{inventory_root}.json"
        manifest_path.write_text(json.dumps(manifest.model_dump(mode="json")), encoding="utf-8")

        with pytest.raises(CorpusIntegrityError, match=expected_code):
            load_verified_corpus(manifest_path, repository_root=tmp_path)


def test_inventory_root_cannot_escape_repository(tmp_path: Path) -> None:
    source_path = tmp_path / "source.md"
    source_path.write_text("trusted\n", encoding="utf-8")
    manifest = CorpusManifest(
        schema_version=1,
        corpus_generation="test-generation",
        as_of_date=AS_OF_DATE,
        active_jurisdictions=("India",),
        active_topics=("gratuity",),
        production_legal_reviewed=False,
        inventory_roots=("../outside",),
        sources=(_source(relative_path="source.md", content_sha256=_sha256(source_path)),),
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(mode="json")), encoding="utf-8")

    with pytest.raises(CorpusIntegrityError, match="SOURCE_PATH_ESCAPE"):
        load_verified_corpus(manifest_path, repository_root=tmp_path)


def test_invalid_manifest_and_non_utf8_policy_fail_with_stable_codes(tmp_path: Path) -> None:
    invalid_manifest = tmp_path / "invalid.json"
    invalid_manifest.write_text("not-json", encoding="utf-8")
    with pytest.raises(CorpusIntegrityError, match="MANIFEST_INVALID"):
        load_verified_corpus(invalid_manifest, repository_root=tmp_path)

    policy_path = tmp_path / "policy.md"
    policy_path.write_bytes(b"\xff\xfe")
    policy = _source(
        source_id="fictional-policy",
        relative_path="policy.md",
        content_sha256=hashlib.sha256(b"\xff\xfe").hexdigest(),
        normative_tier=NormativeTier.COMPANY_POLICY,
        synthetic=True,
        certification_level=CertificationLevel.DEMO_POLICY_REVIEWED,
        official_source_urls=(),
    )
    manifest = CorpusManifest(
        schema_version=1,
        corpus_generation="test-generation",
        as_of_date=AS_OF_DATE,
        active_jurisdictions=("India",),
        active_topics=("gratuity",),
        production_legal_reviewed=False,
        inventory_roots=(),
        sources=(policy,),
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(mode="json")), encoding="utf-8")

    with pytest.raises(CorpusIntegrityError, match="SOURCE_ENCODING_INVALID"):
        load_verified_corpus(manifest_path, repository_root=tmp_path)


def test_source_hash_is_stable_across_bom_and_line_endings(tmp_path: Path) -> None:
    source_path = tmp_path / "source.md"
    source_path.write_bytes(b"\xef\xbb\xbftrusted\r\ncontent\r\n")
    canonical_hash = hashlib.sha256(b"trusted\ncontent\n").hexdigest()
    source = _source(relative_path="source.md", content_sha256=canonical_hash)
    manifest = CorpusManifest(
        schema_version=1,
        corpus_generation="test-generation",
        as_of_date=AS_OF_DATE,
        active_jurisdictions=("India",),
        active_topics=("gratuity",),
        production_legal_reviewed=False,
        inventory_roots=(),
        sources=(source,),
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(mode="json")), encoding="utf-8")

    verified = load_verified_corpus(manifest_path, repository_root=tmp_path)
    assert verified.serving_sources == (source,)


def test_binary_source_uses_raw_bytes_and_inventory_covers_pdf(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    pdf_path = raw_dir / "law.pdf"
    pdf_bytes = b"%PDF-1.7\nphase-2b-fixture\r\n%%EOF\n"
    pdf_path.write_bytes(pdf_bytes)
    source = _source(
        relative_path="raw/law.pdf",
        media_type=SourceMediaType.PDF,
        content_sha256=hashlib.sha256(pdf_bytes).hexdigest(),
    )
    manifest = CorpusManifest(
        schema_version=2,
        corpus_generation="test-generation",
        as_of_date=AS_OF_DATE,
        active_jurisdictions=("India",),
        active_topics=("gratuity",),
        production_legal_reviewed=False,
        inventory_roots=("raw",),
        sources=(source,),
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(mode="json")), encoding="utf-8")

    verified = load_verified_corpus(manifest_path, repository_root=tmp_path)
    assert verified.serving_sources == (source,)

    (raw_dir / "unrecorded.pdf").write_bytes(pdf_bytes)
    with pytest.raises(CorpusIntegrityError, match="UNACCOUNTED_SOURCE"):
        load_verified_corpus(manifest_path, repository_root=tmp_path)


def test_manifest_rejects_invalid_document_metadata_and_lineage() -> None:
    with pytest.raises(ValidationError, match="effective_to"):
        _source(effective_to=dt.date(2025, 11, 21))

    with pytest.raises(ValidationError, match="reviewed_on"):
        _source(reviewed_on=None)

    current = _source(
        source_id="current",
        effective_from=dt.date(2026, 1, 1),
        supersedes=("missing-prior",),
    )
    with pytest.raises(ValidationError, match="unknown source"):
        CorpusManifest(
            schema_version=2,
            corpus_generation="test-generation",
            as_of_date=AS_OF_DATE,
            active_jurisdictions=("India",),
            active_topics=("gratuity",),
            production_legal_reviewed=False,
            inventory_roots=(),
            sources=(current,),
        )

    prior = _source(
        source_id="prior",
        relative_path="prior.md",
        document_version="1",
        effective_from=dt.date(2025, 1, 1),
        effective_to=dt.date(2026, 1, 1),
    )
    successor = _source(
        source_id="successor",
        relative_path="successor.md",
        document_version="2",
        effective_from=dt.date(2026, 1, 1),
        supersedes=("prior",),
    )
    manifest = CorpusManifest(
        schema_version=2,
        corpus_generation="test-generation",
        as_of_date=AS_OF_DATE,
        active_jurisdictions=("India",),
        active_topics=("gratuity",),
        production_legal_reviewed=False,
        inventory_roots=(),
        sources=(prior, successor),
    )
    assert manifest.sources[-1].supersedes == ("prior",)


def test_source_extension_must_match_declared_media_type(tmp_path: Path) -> None:
    source_path = tmp_path / "law.md"
    source_path.write_text("trusted\n", encoding="utf-8")
    source = _source(
        relative_path="law.md",
        media_type=SourceMediaType.PDF,
        content_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
    )
    manifest = CorpusManifest(
        schema_version=2,
        corpus_generation="test-generation",
        as_of_date=AS_OF_DATE,
        active_jurisdictions=("India",),
        active_topics=("gratuity",),
        production_legal_reviewed=False,
        inventory_roots=(),
        sources=(source,),
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(mode="json")), encoding="utf-8")

    with pytest.raises(CorpusIntegrityError, match="SOURCE_MEDIA_TYPE_MISMATCH"):
        load_verified_corpus(manifest_path, repository_root=tmp_path)


def test_official_artifact_acquisition_evidence_matches_manifest_and_files() -> None:
    verified = load_verified_corpus(MANIFEST_PATH, repository_root=REPOSITORY_ROOT)
    by_id = {source.source_id: source for source in verified.manifest.sources}
    acquisition = json.loads(ACQUISITION_STATUS_PATH.read_text(encoding="utf-8"))
    local_artifacts = acquisition["locally_verified_official_artifacts"]

    assert sum(item["pages"] for item in local_artifacts) >= 150
    assert sum(item["extracted_word_count_for_profile_only"] for item in local_artifacts) >= 80_000
    for item in local_artifacts:
        source = by_id[item["source_id"]]
        path = REPOSITORY_ROOT / source.relative_path
        assert source.use is CorpusUse.SERVING
        assert source.media_type is SourceMediaType.PDF
        assert source.content_sha256 == item["sha256"]
        assert path.stat().st_size == item["bytes"]

    assert all(
        item["status"] == "REMOTE_ONLY" and item["reason"] for item in acquisition["remote_only_official_artifacts"]
    )
