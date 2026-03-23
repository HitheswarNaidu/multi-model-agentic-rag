import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from rag.config import Settings
from rag.ingestion.parser import LlamaParseError, parse_document, _blocks_from_json

# Create a fake llama_parse module so the lazy import inside
# parse_document resolves without the real package installed.
_fake_llama_mod = ModuleType("llama_parse")
_fake_llama_mod.LlamaParse = MagicMock  # type: ignore[attr-defined]


def _mock_md_result(pages_md):
    """Mock that returns markdown docs and no JSON."""
    docs = []
    for md in pages_md:
        doc = MagicMock()
        doc.text = md
        docs.append(doc)
    result = MagicMock()
    result.get_json_result.return_value = []  # no JSON
    result.get_markdown_documents.return_value = docs
    return result


def _mock_json_result(pages):
    """Mock that returns structured JSON pages."""
    result = MagicMock()
    result.get_json_result.return_value = [{"pages": pages}]
    result.get_markdown_documents.return_value = []
    return result


# ---------------------------------------------------------------------------
# JSON mode tests
# ---------------------------------------------------------------------------

def test_blocks_from_json_extracts_sections():
    pages = [
        {
            "page": 1,
            "items": [
                {"type": "heading", "value": "Experience"},
                {"type": "text", "value": "Software Developer at Acme Corp."},
                {"type": "heading", "value": "Projects"},
                {"type": "text", "value": "Built an agentic chess system."},
            ],
        }
    ]
    blocks = _blocks_from_json("test.pdf", pages)
    assert len(blocks) == 4
    # First heading itself
    assert blocks[0].section == "Experience"
    assert blocks[0].chunk_type == "paragraph"
    # Text under Experience
    assert blocks[1].section == "Experience"
    # Second heading
    assert blocks[2].section == "Projects"
    # Text under Projects
    assert blocks[3].section == "Projects"


def test_blocks_from_json_tables():
    pages = [
        {
            "page": 2,
            "items": [
                {"type": "table", "value": "| A | B |\n|---|---|\n| 1 | 2 |"},
            ],
        }
    ]
    blocks = _blocks_from_json("test.pdf", pages)
    assert len(blocks) == 1
    assert blocks[0].chunk_type == "table"
    assert blocks[0].table_id == "table-2-1"
    assert blocks[0].page == 2


def test_blocks_from_json_figures():
    pages = [
        {
            "page": 1,
            "items": [
                {"type": "figure", "value": "Architecture diagram"},
            ],
        }
    ]
    blocks = _blocks_from_json("test.pdf", pages)
    assert len(blocks) == 1
    assert blocks[0].chunk_type == "figure"


def test_blocks_from_json_empty_items_skipped():
    pages = [{"page": 1, "items": [{"type": "text", "value": ""}]}]
    blocks = _blocks_from_json("test.pdf", pages)
    assert len(blocks) == 0


@patch.dict(sys.modules, {"llama_parse": _fake_llama_mod})
@patch("llama_parse.LlamaParse")
def test_parse_json_mode(mock_cls, tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    mock_cls.return_value.parse.return_value = _mock_json_result([
        {
            "page": 1,
            "items": [
                {"type": "heading", "value": "Title"},
                {"type": "text", "value": "Body text here."},
            ],
        },
        {
            "page": 2,
            "items": [
                {"type": "table", "value": "| Col |\n|---|\n| val |"},
            ],
        },
    ])
    settings = Settings(llama_cloud_api_key="llx-test")
    result = parse_document(pdf, settings=settings)
    assert result.parse_meta["parse_mode"] == "json"
    assert len(result.blocks) == 3
    assert result.blocks[0].section == "Title"
    assert result.blocks[2].chunk_type == "table"


# ---------------------------------------------------------------------------
# Markdown fallback tests (existing behavior preserved)
# ---------------------------------------------------------------------------

@patch.dict(sys.modules, {"llama_parse": _fake_llama_mod})
@patch("llama_parse.LlamaParse")
def test_parse_pdf_returns_blocks(mock_cls, tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    mock_cls.return_value.parse.return_value = _mock_md_result(
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
    assert result.parse_meta["parse_mode"] == "markdown"


@patch.dict(sys.modules, {"llama_parse": _fake_llama_mod})
@patch("llama_parse.LlamaParse")
def test_parse_empty_result_raises(mock_cls, tmp_path):
    pdf = tmp_path / "empty.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    mock_cls.return_value.parse.return_value = _mock_md_result([])
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
    mock_cls.return_value.parse.return_value = _mock_md_result(["Word document content"])
    settings = Settings(llama_cloud_api_key="llx-test")
    result = parse_document(docx, settings=settings)
    assert len(result.blocks) == 1
    assert result.blocks[0].doc_id == "test.docx"
