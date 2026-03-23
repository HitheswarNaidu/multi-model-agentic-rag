from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from rag.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class Block:
    doc_id: str
    page: int
    chunk_type: str
    text: str
    confidence: float
    section: str | None = None
    table_id: str | None = None


@dataclass
class DocumentParseResult:
    blocks: list[Block]
    parse_meta: dict[str, object] = field(default_factory=dict)


class LlamaParseError(RuntimeError):
    code = "LLAMAPARSE_FAILED"


# ---------------------------------------------------------------------------
# JSON result → Block helpers
# ---------------------------------------------------------------------------

_TYPE_MAP = {
    "heading": "paragraph",
    "text": "paragraph",
    "paragraph": "paragraph",
    "table": "table",
    "figure": "figure",
    "image": "figure",
}


def _blocks_from_json(doc_id: str, json_pages: list[dict]) -> list[Block]:
    """Convert LlamaParse JSON pages into typed Blocks with section tracking."""
    blocks: list[Block] = []
    current_section: str | None = None
    table_counter = 0

    for page_data in json_pages:
        page_num = page_data.get("page", 1)
        items = page_data.get("items", [])

        for item in items:
            item_type = item.get("type", "text").lower()
            text = item.get("value", item.get("text", item.get("md", ""))).strip()
            if not text:
                continue

            # Track section headings
            if item_type in ("heading", "title", "section_heading"):
                current_section = text
                # Still emit headings as paragraph blocks so they get indexed
                blocks.append(Block(
                    doc_id=doc_id,
                    page=page_num,
                    chunk_type="paragraph",
                    text=text,
                    confidence=0.95,
                    section=current_section,
                ))
                continue

            mapped_type = _TYPE_MAP.get(item_type, "paragraph")

            table_id = None
            if mapped_type == "table":
                table_counter += 1
                table_id = f"table-{page_num}-{table_counter}"

            blocks.append(Block(
                doc_id=doc_id,
                page=page_num,
                chunk_type=mapped_type,
                text=text,
                confidence=0.95,
                section=current_section,
                table_id=table_id,
            ))

    return blocks


def _blocks_from_markdown(doc_id: str, docs: list) -> list[Block]:
    """Fallback: convert markdown page documents into Blocks."""
    blocks: list[Block] = []
    for page_idx, doc in enumerate(docs, start=1):
        text = (doc.text if hasattr(doc, "text") else str(doc)).strip()
        if not text:
            continue
        blocks.append(Block(
            doc_id=doc_id,
            page=page_idx,
            chunk_type="paragraph",
            text=text,
            confidence=0.95,
        ))
    return blocks


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_document(path: Path, settings: Settings | None = None) -> DocumentParseResult:
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    runtime_settings = settings or get_settings()
    api_key = runtime_settings.llama_cloud_api_key

    if not api_key:
        raise LlamaParseError(
            "LLAMA_CLOUD_API_KEY is not set. "
            "Obtain a key from https://cloud.llamaindex.ai/api-key"
        )

    from llama_parse import LlamaParse

    try:
        parser = LlamaParse(
            api_key=api_key,
            result_type="json",
            num_workers=runtime_settings.ingestion_parse_workers,
            language="en",
        )
        result = parser.parse(str(path))
    except Exception as exc:
        raise LlamaParseError(f"LlamaParse failed for {path}: {exc}") from exc

    # Try JSON result first for structured extraction
    blocks: list[Block] = []
    parse_mode = "json"

    try:
        json_result = result.get_json_result()
        if json_result and isinstance(json_result, list) and len(json_result) > 0:
            # json_result is a list of dicts, one per file; each has "pages"
            pages = json_result[0].get("pages", [])
            if pages:
                blocks = _blocks_from_json(path.name, pages)
    except Exception:
        logger.debug("JSON extraction failed for %s, falling back to markdown", path)

    # Fallback to markdown if JSON yielded nothing
    if not blocks:
        parse_mode = "markdown"
        try:
            docs = result.get_markdown_documents(split_by_page=True)
            if docs:
                blocks = _blocks_from_markdown(path.name, docs)
        except Exception:
            pass

    if not blocks:
        raise LlamaParseError(f"LlamaParse returned no content for {path}")

    return DocumentParseResult(
        blocks=blocks,
        parse_meta={"parser_used": "llamaparse", "parse_mode": parse_mode},
    )
