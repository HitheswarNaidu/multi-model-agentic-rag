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
            num_workers=runtime_settings.ingestion_parse_workers,
            language="en",
        )
        result = parser.parse(str(path))
    except Exception as exc:
        raise LlamaParseError(f"LlamaParse failed for {path}: {exc}") from exc

    docs = result.get_markdown_documents(split_by_page=True)
    if not docs:
        raise LlamaParseError(f"LlamaParse returned no content for {path}")

    blocks: list[Block] = []
    for page_idx, doc in enumerate(docs, start=1):
        text = (doc.text if hasattr(doc, "text") else str(doc)).strip()
        if not text:
            continue
        blocks.append(
            Block(
                doc_id=path.name,
                page=page_idx,
                chunk_type="paragraph",
                text=text,
                confidence=0.95,
            )
        )

    if not blocks:
        raise LlamaParseError(f"LlamaParse parsed no text from {path}")

    return DocumentParseResult(
        blocks=blocks,
        parse_meta={"parser_used": "llamaparse"},
    )
