from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest
from pydantic import HttpUrl, ValidationError
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from hr_policy_rag.corpus import (
    CertificationLevel,
    CorpusUse,
    ManifestSource,
    PdfPageRange,
    SourceKind,
    SourceMediaType,
    load_verified_corpus,
)
from hr_policy_rag.domain import NormativeTier
from hr_policy_rag.ingestion import (
    ChunkingConfig,
    IngestionError,
    build_ingestion_bundle,
    render_chunks_jsonl,
    render_ingestion_manifest,
)
from hr_policy_rag.ingestion.parsers import parse_markdown, parse_pdf, parse_source

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CORPUS_MANIFEST_PATH = REPOSITORY_ROOT / "corpus_v2" / "manifest.json"
INGESTION_MANIFEST_PATH = REPOSITORY_ROOT / "artifacts" / "v2" / "ingestion" / "manifest.json"
CHUNKS_PATH = REPOSITORY_ROOT / "artifacts" / "v2" / "ingestion" / "chunks.jsonl"


def _pdf_source(path: Path, *page_ranges: PdfPageRange) -> ManifestSource:
    return ManifestSource(
        source_id="pdf-test-source",
        title="PDF test source",
        document_version="1",
        relative_path=path.name,
        content_sha256="a" * 64,
        media_type=SourceMediaType.PDF,
        source_kind=SourceKind.PRIMARY_LAW,
        use=CorpusUse.SERVING,
        jurisdiction="India",
        topics=("gratuity",),
        normative_tier=NormativeTier.STATUTORY,
        synthetic=False,
        certification_level=CertificationLevel.PRIMARY_SOURCE_CHECKED,
        official_source_urls=(HttpUrl("https://www.labour.gov.in/test.pdf"),),
        approved_locators=("Test locator",),
        approved_page_ranges=page_ranges or (PdfPageRange(start_page=1, end_page=1),),
        published_on=dt.date(2026, 1, 1),
        effective_from=dt.date(2026, 1, 1),
        reviewed_on=dt.date(2026, 1, 1),
    )


def _markdown_source(path: Path, *, media_type: SourceMediaType = SourceMediaType.MARKDOWN) -> ManifestSource:
    return ManifestSource(
        source_id="markdown-test-source",
        title="Markdown test source",
        document_version="1",
        relative_path=path.name,
        content_sha256="b" * 64,
        media_type=media_type,
        source_kind=SourceKind.COMPANY_POLICY,
        use=CorpusUse.SERVING,
        jurisdiction="India",
        topics=("leave",),
        normative_tier=NormativeTier.COMPANY_POLICY,
        synthetic=True,
        certification_level=CertificationLevel.DEMO_POLICY_REVIEWED,
        published_on=dt.date(2026, 1, 1),
        effective_from=dt.date(2026, 1, 1),
        reviewed_on=dt.date(2026, 1, 1),
    )


def _bundle():
    corpus = load_verified_corpus(CORPUS_MANIFEST_PATH, repository_root=REPOSITORY_ROOT)
    return corpus, build_ingestion_bundle(corpus, repository_root=REPOSITORY_ROOT)


def test_phase_3_artifact_is_complete_reproducible_and_checked_in() -> None:
    corpus, first = _bundle()
    second = build_ingestion_bundle(corpus, repository_root=REPOSITORY_ROOT)
    chunks_jsonl = render_chunks_jsonl(first.chunks)
    manifest_json = render_ingestion_manifest(first.manifest)

    assert chunks_jsonl == render_chunks_jsonl(second.chunks)
    assert manifest_json == render_ingestion_manifest(second.manifest)
    assert chunks_jsonl == CHUNKS_PATH.read_text(encoding="utf-8")
    assert manifest_json == INGESTION_MANIFEST_PATH.read_text(encoding="utf-8")
    assert first.manifest.corpus_generation == corpus.manifest.corpus_generation
    assert first.manifest.corpus_sha256 == corpus.corpus_sha256
    assert first.manifest.source_count == len(corpus.serving_sources) == 33
    assert first.manifest.chunk_count == len(first.chunks) > first.manifest.source_count
    assert len(first.manifest.chunks_sha256) == 64
    assert len(first.manifest.ingestion_generation) == 64


def test_every_serving_source_and_only_serving_sources_produce_chunks() -> None:
    corpus, bundle = _bundle()
    serving_ids = {source.source_id for source in corpus.serving_sources}
    chunk_source_ids = {chunk.source_id for chunk in bundle.chunks}
    excluded_ids = {source.source_id for source in corpus.manifest.sources if source.use is not CorpusUse.SERVING}

    assert chunk_source_ids == serving_ids
    assert chunk_source_ids.isdisjoint(excluded_ids)
    assert len({chunk.chunk_id for chunk in bundle.chunks}) == len(bundle.chunks)
    assert len({(chunk.source_id, chunk.chunk_index) for chunk in bundle.chunks}) == len(bundle.chunks)


def test_chunks_preserve_complete_provenance_and_quality_bounds() -> None:
    corpus, bundle = _bundle()
    sources = {source.source_id: source for source in corpus.serving_sources}
    config = ChunkingConfig()

    for chunk in bundle.chunks:
        source = sources[chunk.source_id]
        assert chunk.source_content_sha256 == source.content_sha256
        assert chunk.document_version == source.document_version
        assert chunk.jurisdiction == source.jurisdiction
        assert chunk.topics == source.topics
        assert chunk.normative_tier is source.normative_tier
        assert chunk.source_kind is source.source_kind
        assert chunk.effective_from == source.effective_from
        assert chunk.effective_to == source.effective_to
        assert chunk.supersedes == source.supersedes
        assert chunk.approved_locators == source.approved_locators
        assert chunk.text == chunk.text.strip()
        assert "\x00" not in chunk.text
        assert "\ufffd" not in chunk.text
        assert 1 <= len(chunk.text) <= config.max_chars
        assert len(chunk.text_sha256) == 64
        assert chunk.locator


def test_pdf_chunks_are_restricted_to_approved_pages() -> None:
    corpus, bundle = _bundle()
    pdf_sources = {
        source.source_id: source for source in corpus.serving_sources if source.media_type is SourceMediaType.PDF
    }
    observed_pages: dict[str, set[int]] = {source_id: set() for source_id in pdf_sources}

    for chunk in bundle.chunks:
        if chunk.source_id not in pdf_sources:
            assert chunk.page_number is None
            continue
        assert chunk.page_number is not None
        observed_pages[chunk.source_id].add(chunk.page_number)

    for source_id, source in pdf_sources.items():
        approved_pages = {
            page
            for page_range in source.approved_page_ranges
            for page in range(page_range.start_page, page_range.end_page + 1)
        }
        assert observed_pages[source_id] == approved_pages


def test_critical_legal_passages_survive_pdf_extraction() -> None:
    _, bundle = _bundle()
    by_source: dict[str, str] = {}
    for chunk in bundle.chunks:
        by_source[chunk.source_id] = f"{by_source.get(chunk.source_id, '')}\n{chunk.text}"

    assert "continuous service for not less than five years" in by_source["in-coss-2020-raw"]
    assert "one-half" in by_source["in-wages-2019-raw"]
    assert "applicable w.e.f. 21.11.2025" in by_source["in-labour-codes-faq-2026-03-16-raw"]
    assert "The Code on Wages, 2019, amalgamates 4" in by_source["in-labour-codes-employer-handbook-2026-raw"]
    assert all(
        len(chunk.text) >= 200
        for chunk in bundle.chunks
        if chunk.source_id == "in-labour-codes-employer-handbook-2026-raw"
    )


def test_adversarial_payloads_do_not_leak_into_chunks() -> None:
    _, bundle = _bundle()
    chunk_text = "\n".join(chunk.text for chunk in bundle.chunks)

    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" not in chunk_text
    assert "four years is sufficient" not in chunk_text
    assert "gross salary must replace basic wage" not in chunk_text


def test_markdown_chunking_preserves_heading_locator() -> None:
    _, bundle = _bundle()
    policy_chunks = [chunk for chunk in bundle.chunks if chunk.source_id == "meridian-india-gratuity-policy-2025"]

    assert policy_chunks
    assert all(chunk.page_number is None for chunk in policy_chunks)
    assert any("MER-IN-GRATUITY-V2" in chunk.locator for chunk in policy_chunks)
    assert any("MER-IN-GRATUITY-FACTS-REQUIRED" in chunk.locator for chunk in policy_chunks)


def test_parser_warnings_are_recorded_instead_of_hidden() -> None:
    _, bundle = _bundle()
    summaries = {summary.source_id: summary for summary in bundle.manifest.sources}

    assert summaries["in-wages-2019-raw"].warnings == (
        "Xref table not zero-indexed. ID numbers for objects will be corrected.",
    )
    assert summaries["in-coss-2020-raw"].warnings == ()


def test_pdf_page_range_contract_rejects_invalid_or_overlapping_ranges() -> None:
    with pytest.raises(ValidationError, match="greater than or equal to 1"):
        PdfPageRange(start_page=0, end_page=1)
    with pytest.raises(ValidationError, match="end_page must be on or after start_page"):
        PdfPageRange(start_page=4, end_page=3)
    with pytest.raises(ValidationError, match="must not overlap"):
        _pdf_source(
            Path("law.pdf"),
            PdfPageRange(start_page=1, end_page=2),
            PdfPageRange(start_page=2, end_page=3),
        )


def test_typed_ingestion_errors_are_stable() -> None:
    error = IngestionError("UNSUPPORTED_MEDIA_TYPE", "source-1", "text/html")

    assert error.code == "UNSUPPORTED_MEDIA_TYPE"
    assert error.source_id == "source-1"
    assert error.detail == "text/html"
    assert str(error) == "UNSUPPORTED_MEDIA_TYPE [source-1]: text/html"


def test_checked_in_chunks_are_valid_individual_json_records() -> None:
    records = [json.loads(line) for line in CHUNKS_PATH.read_text(encoding="utf-8").splitlines()]

    assert records
    assert all(record["schema_version"] == 1 for record in records)
    assert all(record["chunk_id"].startswith("chk_") for record in records)


def test_pdf_parser_rejects_malformed_encrypted_and_textless_files(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.pdf"
    malformed.write_bytes(b"%PDF-1.7\nnot-a-valid-pdf")
    with pytest.raises(IngestionError, match="PDF_READ_FAILED"):
        parse_pdf(_pdf_source(malformed), malformed)

    encrypted = tmp_path / "encrypted.pdf"
    encrypted_writer = PdfWriter()
    encrypted_writer.add_blank_page(width=100, height=100)
    encrypted_writer.encrypt("secret")
    with encrypted.open("wb") as stream:
        encrypted_writer.write(stream)
    with pytest.raises(IngestionError, match="PDF_ENCRYPTED"):
        parse_pdf(_pdf_source(encrypted), encrypted)

    textless = tmp_path / "textless.pdf"
    textless_writer = PdfWriter()
    textless_writer.add_blank_page(width=100, height=100)
    with textless.open("wb") as stream:
        textless_writer.write(stream)
    with pytest.raises(IngestionError, match="PDF_TEXT_MISSING"):
        parse_pdf(_pdf_source(textless), textless)


def test_pdf_parser_rejects_oversized_stream_and_out_of_range_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf_path = tmp_path / "content.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(width=100, height=100)
    content = DecodedStreamObject()
    content.set_data(b"q Q")
    page[NameObject("/Contents")] = content
    with pdf_path.open("wb") as stream:
        writer.write(stream)

    monkeypatch.setattr("hr_policy_rag.ingestion.parsers.MAX_PDF_CONTENT_STREAM_BYTES", 1)
    with pytest.raises(IngestionError, match="PDF_PAGE_TOO_LARGE"):
        parse_pdf(_pdf_source(pdf_path), pdf_path)

    with pytest.raises(IngestionError, match="PDF_PAGE_RANGE_INVALID"):
        parse_pdf(_pdf_source(pdf_path, PdfPageRange(start_page=2, end_page=2)), pdf_path)


def test_malformed_clause_markdown_and_unsupported_media_fail_closed(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.md"
    malformed.write_text("# Policy\n\n---\nclause_id: ONLY-ID\n", encoding="utf-8")
    with pytest.raises(IngestionError, match="MARKDOWN_CLAUSE_BLOCK_INVALID"):
        parse_markdown(_markdown_source(malformed), malformed)

    html = tmp_path / "policy.html"
    html.write_text(
        "SYNTHETIC DOCUMENT — NOT A REAL COMPANY POLICY. <p>Policy</p>",
        encoding="utf-8",
    )
    with pytest.raises(IngestionError, match="UNSUPPORTED_MEDIA_TYPE"):
        parse_source(_markdown_source(html, media_type=SourceMediaType.HTML), html)


def test_clause_metadata_is_a_locator_not_embedding_content() -> None:
    _, bundle = _bundle()
    policy_text = "\n".join(
        chunk.text for chunk in bundle.chunks if chunk.source_id == "meridian-india-gratuity-policy-2025"
    )

    assert "temporal_applicability:" not in policy_text
    assert "certification:" not in policy_text
