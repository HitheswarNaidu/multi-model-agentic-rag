from typing import Iterable, List

from rag.chunking.metadata import ChunkMetadata, DocumentChunk
from rag.ingestion.parser import Block


def _window(text: str, max_chars: int, overlap: int) -> List[str]:
    if max_chars <= 0:
        return [text]
    parts: List[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(length, start + max_chars)
        parts.append(text[start:end].strip())
        if end == length:
            break
        start = max(0, end - overlap)
    return [p for p in parts if p]


def chunk_blocks(
    blocks: Iterable[Block],
    doc_type: str,
    max_chars: int = 800,
    overlap: int = 80,
) -> List[DocumentChunk]:
    chunks: List[DocumentChunk] = []
    counter = 0
    for block in blocks:
        text = block.text.strip()
        if not text:
            continue
        # Combine figure with caption if present via table_id as a loose link (if parser supplies)
        if block.chunk_type == "figure" and block.table_id:
            text = f"{text}\nCaption: {block.table_id}"
        
        if block.chunk_type == "table":
            # For tables, we split by row to enable precise row-level retrieval
            rows = text.split('\n')
            for i, row in enumerate(rows):
                row_text = row.strip()
                if not row_text:
                    continue
                chunk_id = f"{block.doc_id}-{block.page}-{counter}-row-{i}"
                meta = ChunkMetadata(
                    doc_id=block.doc_id,
                    doc_type=doc_type,
                    page=block.page,
                    section=block.section or "",
                    chunk_id=chunk_id,
                    chunk_type="row",  # Transform 'table' block into 'row' chunks
                    table_id=block.table_id,
                    confidence=block.confidence,
                )
                chunks.append(DocumentChunk(metadata=meta, content=row_text))
            counter += 1
            continue

        windows = _window(text, max_chars=max_chars, overlap=overlap)
        for win in windows:
            chunk_id = f"{block.doc_id}-{block.page}-{counter}"
            meta = ChunkMetadata(
                doc_id=block.doc_id,
                doc_type=doc_type,
                page=block.page,
                section=block.section or "",
                chunk_id=chunk_id,
                chunk_type=block.chunk_type,
                table_id=block.table_id,
                confidence=block.confidence,
            )
            chunks.append(DocumentChunk(metadata=meta, content=win))
            counter += 1
    return chunks
