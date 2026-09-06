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
    load_verified_corpus,
)
from hr_policy_rag.domain import NormativeTier

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPOSITORY_ROOT / "corpus_v2" / "manifest.json"
AS_OF_DATE = dt.date(2026, 9, 6)


def _sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    canonical_bytes = text.replace("\r\n", "\n").replace("\r", "\n").encode()
    return hashlib.sha256(canonical_bytes).hexdigest()


def _source(**overrides: object) -> ManifestSource:
    values: dict[str, object] = {
        "source_id": "india-gratuity-law",
        "relative_path": "corpus_v2/sources/india/gratuity_statutory_extract.md",
        "content_sha256": "a" * 64,
        "use": CorpusUse.SERVING,
        "jurisdiction": "India",
        "topics": ("gratuity",),
        "normative_tier": NormativeTier.STATUTORY,
        "synthetic": False,
        "certification_level": CertificationLevel.PRIMARY_SOURCE_CHECKED,
        "official_source_urls": ("https://www.labour.gov.in/example.pdf",),
        "reason_codes": (),
    }
    values.update(overrides)
    return ManifestSource.model_validate(values)


def test_committed_manifest_exposes_only_certified_india_gratuity_sources() -> None:
    verified = load_verified_corpus(MANIFEST_PATH, repository_root=REPOSITORY_ROOT)

    assert verified.manifest.active_jurisdictions == ("India",)
    assert verified.manifest.active_topics == ("gratuity",)
    assert {source.source_id for source in verified.serving_sources} == {
        "in-coss-2020-gratuity-demo-extract",
        "meridian-india-gratuity-policy-v1",
    }
    assert all(source.use is CorpusUse.SERVING for source in verified.serving_sources)
    assert not verified.manifest.production_legal_reviewed
    assert len(verified.corpus_sha256) == 64


def test_every_legacy_markdown_source_is_explicitly_non_serving() -> None:
    verified = load_verified_corpus(MANIFEST_PATH, repository_root=REPOSITORY_ROOT)
    recorded = {source.relative_path: source for source in verified.manifest.sources}
    legacy_paths = {path.relative_to(REPOSITORY_ROOT).as_posix() for path in (REPOSITORY_ROOT / "corpus").rglob("*.md")}

    assert legacy_paths <= recorded.keys()
    assert all(recorded[path].use is not CorpusUse.SERVING for path in legacy_paths)


def test_certified_legal_facts_exclude_the_v1_falsehood_and_record_scope_limit() -> None:
    verified = load_verified_corpus(MANIFEST_PATH, repository_root=REPOSITORY_ROOT)
    serving_text = "\n".join(
        (REPOSITORY_ROOT / source.relative_path).read_text(encoding="utf-8") for source in verified.serving_sources
    )

    assert "five years" in serving_text
    assert "one year" in serving_text
    assert "21 November 2025" in serving_text
    assert "four years" not in serving_text
    assert "does not\nstate a monetary ceiling" in serving_text


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
