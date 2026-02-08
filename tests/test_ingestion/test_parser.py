from pathlib import Path

import pytest

from rag.config import get_settings
from rag.ingestion.parser import Block, DocumentParseResult, OCRConfigurationError, parse_document


def test_parse_document_missing_file():
    with pytest.raises(FileNotFoundError):
        parse_document(Path("/no/such/file.pdf"))


def test_parse_document_pdf(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DOCLING_OCR_FORCE", "true")
    get_settings.cache_clear()
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF")
    with pytest.raises(OCRConfigurationError):
        parse_document(pdf_path)


def test_parse_document_fast_text_first_uses_pymupdf_when_sufficient(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DOCLING_OCR_FORCE", "false")
    monkeypatch.setenv("PDF_PARSE_STRATEGY", "fast_text_first")
    monkeypatch.setenv("PDF_TEXT_MIN_CHARS", "1")
    get_settings.cache_clear()
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF")
    monkeypatch.setattr(
        "rag.ingestion.parser._parse_with_pymupdf",
        lambda _: DocumentParseResult(
            blocks=[
                Block(
                    doc_id="sample.pdf",
                    page=1,
                    chunk_type="paragraph",
                    text="enough text",
                    confidence=1.0,
                )
            ]
        ),
    )
    result = parse_document(pdf_path)
    assert isinstance(result, DocumentParseResult)
    assert result.blocks is not None
    assert result.parse_meta.get("parser_strategy") == "fast_text_first"


def test_parse_document_docling_first_falls_back_to_pymupdf(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DOCLING_OCR_FORCE", "false")
    monkeypatch.setenv("PDF_PARSE_STRATEGY", "docling_first")
    get_settings.cache_clear()
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF")
    result = parse_document(pdf_path)
    assert isinstance(result, DocumentParseResult)
    assert result.parse_meta.get("parser_strategy") == "docling_first"
    assert result.parse_meta.get("parser_used") in {"pymupdf", "docling"}


def test_parse_document_fast_text_first_uses_docling_ocr_on_low_text(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DOCLING_OCR_FORCE", "false")
    monkeypatch.setenv("DOCLING_OCR_AUTO", "true")
    monkeypatch.setenv("PDF_PARSE_STRATEGY", "fast_text_first")
    monkeypatch.setenv("PDF_TEXT_MIN_CHARS", "50")
    get_settings.cache_clear()

    pdf_path = tmp_path / "scan_like.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF")

    monkeypatch.setattr(
        "rag.ingestion.parser._parse_with_pymupdf",
        lambda _: DocumentParseResult(
            blocks=[
                Block(
                    doc_id="scan_like.pdf",
                    page=1,
                    chunk_type="paragraph",
                    text="tiny",
                    confidence=1.0,
                )
            ]
        ),
    )

    def fake_docling(path: Path, settings, enable_ocr=None):
        assert enable_ocr is True
        return DocumentParseResult(
            blocks=[
                Block(
                    doc_id=path.name,
                    page=1,
                    chunk_type="paragraph",
                    text="ocr extracted text from image pdf",
                    confidence=0.95,
                )
            ]
        )

    monkeypatch.setattr("rag.ingestion.parser._parse_with_docling", fake_docling)
    result = parse_document(pdf_path)
    assert result.parse_meta.get("parser_strategy") == "fast_text_first"
    assert result.parse_meta.get("parser_used") == "docling"
    assert bool(result.parse_meta.get("ocr_enabled")) is True
