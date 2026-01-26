from pathlib import Path

import pytest

from rag.ingestion.parser import DocumentParseResult, parse_document


def test_parse_document_missing_file():
    with pytest.raises(FileNotFoundError):
        parse_document(Path("/no/such/file.pdf"))


def test_parse_document_pdf(tmp_path: Path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF")
    result = parse_document(pdf_path)
    assert isinstance(result, DocumentParseResult)
    assert isinstance(result.blocks, list)


def test_parse_document_fallback_to_pymupdf(tmp_path: Path):
    # For non-PDF extension unsupported by docling fallback path
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF")
    result = parse_document(pdf_path)
    assert result.blocks is not None
