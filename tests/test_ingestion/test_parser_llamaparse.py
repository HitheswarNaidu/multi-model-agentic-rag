import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from rag.config import Settings
from rag.ingestion.parser import LlamaParseError, parse_document

# Create a fake llama_parse module so the lazy import inside
# parse_document resolves without the real package installed.
_fake_llama_mod = ModuleType("llama_parse")
_fake_llama_mod.LlamaParse = MagicMock  # type: ignore[attr-defined]


def _mock_result(pages_md):
    docs = []
    for md in pages_md:
        doc = MagicMock()
        doc.text = md
        docs.append(doc)
    result = MagicMock()
    result.get_markdown_documents.return_value = docs
    return result


@patch.dict(sys.modules, {"llama_parse": _fake_llama_mod})
@patch("llama_parse.LlamaParse")
def test_parse_pdf_returns_blocks(mock_cls, tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    mock_cls.return_value.parse.return_value = _mock_result(
        ["# Page 1\nSome content here.", "# Page 2\nMore content."]
    )
    settings = Settings(llama_cloud_api_key="llx-test")
    result = parse_document(pdf, settings=settings)
    assert len(result.blocks) == 2
    assert result.blocks[0].chunk_type == "paragraph"
    assert "Page 1" in result.blocks[0].text
    assert result.blocks[0].page == 1
    assert result.blocks[1].page == 2
    assert result.parse_meta["parser_used"] == "llamaparse"


@patch.dict(sys.modules, {"llama_parse": _fake_llama_mod})
@patch("llama_parse.LlamaParse")
def test_parse_empty_result_raises(mock_cls, tmp_path):
    pdf = tmp_path / "empty.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    mock_cls.return_value.parse.return_value = _mock_result([])
    settings = Settings(llama_cloud_api_key="llx-test")
    with pytest.raises(LlamaParseError):
        parse_document(pdf, settings=settings)


def test_parse_missing_api_key_raises(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    settings = Settings(llama_cloud_api_key="")
    with pytest.raises(LlamaParseError, match="LLAMA_CLOUD_API_KEY"):
        parse_document(pdf, settings=settings)


def test_parse_file_not_found():
    with pytest.raises(FileNotFoundError):
        parse_document(Path("/nonexistent/file.pdf"))


@patch.dict(sys.modules, {"llama_parse": _fake_llama_mod})
@patch("llama_parse.LlamaParse")
def test_parse_docx(mock_cls, tmp_path):
    docx = tmp_path / "test.docx"
    docx.write_bytes(b"fake docx")
    mock_cls.return_value.parse.return_value = _mock_result(["Word document content"])
    settings = Settings(llama_cloud_api_key="llx-test")
    result = parse_document(docx, settings=settings)
    assert len(result.blocks) == 1
    assert result.blocks[0].doc_id == "test.docx"
