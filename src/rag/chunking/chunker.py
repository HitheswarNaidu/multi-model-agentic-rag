from __future__ import annotations

import re
from collections.abc import Iterable

from rag.chunking.metadata import ChunkMetadata, DocumentChunk
from rag.ingestion.parser import Block


def _window(text: str, max_chars: int, overlap: int) -> list[str]:
    if max_chars <= 0:
        return [text]
    parts: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(length, start + max_chars)
        parts.append(text[start:end].strip())
        if end == length:
            break
        start = max(0, end - overlap)
    return [p for p in parts if p]


def _split_semantic_units(text: str) -> list[tuple[str, str]]:
    units: list[tuple[str, str]] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if len(line) < 100 and (
            line.startswith("#")
            or line.endswith(":")
            or re.fullmatch(r"\d+(?:\.\d+)*\s+.+", line) is not None
        ):
            units.append((line, "heading"))
            continue
        sentences = re.split(r"(?<=[.!?])\s+", line)
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                units.append((sentence, "sentence"))
    if not units and text.strip():
        units.append((text.strip(), "fallback"))
    return units


def _semantic_windows(text: str, max_chars: int, overlap: int) -> list[tuple[str, str, int]]:
    units = _split_semantic_units(text)
    if not units:
        return []

    windows: list[tuple[str, str, int]] = []
    current: list[str] = []
    current_len = 0
    group_idx = 0
    boundary_reason = "semantic_sentence"

    for part, reason in units:
        if current and current_len + len(part) + 1 > max_chars:
            windows.append((" ".join(current).strip(), boundary_reason, group_idx))
            group_idx += 1
            if overlap > 0:
                carry = " ".join(current)
                current = _window(carry, max_chars=overlap, overlap=0)
            else:
                current = []
            current_len = len(" ".join(current))
        current.append(part)
        current_len += len(part) + 1
        boundary_reason = reason

    if current:
        windows.append((" ".join(current).strip(), boundary_reason, group_idx))
    return [item for item in windows if item[0]]


def chunk_blocks(
    blocks: Iterable[Block],
    doc_type: str,
    max_chars: int = 800,
    overlap: int = 80,
    enable_hierarchy: bool = True,
    chunking_mode: str = "window",
) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    counter = 0

    parent_size = max_chars * 3
    parent_overlap = overlap * 2
    semantic_enabled = chunking_mode == "semantic_hybrid"

    for block in blocks:
        text = block.text.strip()
        if not text:
            continue

        if block.chunk_type == "figure" and block.table_id:
            text = f"{text}\nCaption: {block.table_id}"

        if block.chunk_type == "table":
            rows = text.split("\n")
            if len(rows) > 1:
                first = rows[0].strip()
                second = rows[1].strip()
                if first and second and not any(ch.isdigit() for ch in first) and any(
                    ch.isdigit() for ch in second
                ):
                    rows = rows[1:]
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
                    chunk_type="row",
                    table_id=block.table_id,
                    confidence=block.confidence,
                    semantic_group_id=f"{block.doc_id}-P{block.page}-G{counter}",
                    boundary_reason="table_row",
                )
                chunks.append(DocumentChunk(metadata=meta, content=row_text))
            counter += 1
            continue

        if enable_hierarchy:
            parent_windows = _window(text, max_chars=parent_size, overlap=parent_overlap)
            for p_idx, p_text in enumerate(parent_windows):
                parent_id = f"{block.doc_id}-{block.page}-{counter}-P{p_idx}"
                if semantic_enabled:
                    semantic_children = _semantic_windows(
                        p_text,
                        max_chars=max_chars,
                        overlap=overlap,
                    )
                    children = [(c_text, reason, grp) for c_text, reason, grp in semantic_children]
                else:
                    children = [(c_text, "window", c_idx) for c_idx, c_text in enumerate(
                        _window(p_text, max_chars=max_chars, overlap=overlap)
                    )]

                for c_idx, child in enumerate(children):
                    c_text, boundary_reason, semantic_group_idx = child
                    chunk_id = f"{parent_id}-C{c_idx}"
                    semantic_group_id = (
                        f"{block.doc_id}-P{block.page}-G{counter}-{p_idx}-{semantic_group_idx}"
                    )
                    meta = ChunkMetadata(
                        doc_id=block.doc_id,
                        doc_type=doc_type,
                        page=block.page,
                        section=block.section or "",
                        chunk_id=chunk_id,
                        chunk_type=block.chunk_type,
                        table_id=block.table_id,
                        confidence=block.confidence,
                        parent_content=p_text,
                        semantic_group_id=semantic_group_id,
                        boundary_reason=boundary_reason,
                    )
                    chunks.append(DocumentChunk(metadata=meta, content=c_text))

            counter += 1
            continue

        if semantic_enabled:
            semantic_windows = _semantic_windows(text, max_chars=max_chars, overlap=overlap)
            for idx, (win, reason, group_idx) in enumerate(semantic_windows):
                chunk_id = f"{block.doc_id}-{block.page}-{counter}-S{idx}"
                meta = ChunkMetadata(
                    doc_id=block.doc_id,
                    doc_type=doc_type,
                    page=block.page,
                    section=block.section or "",
                    chunk_id=chunk_id,
                    chunk_type=block.chunk_type,
                    table_id=block.table_id,
                    confidence=block.confidence,
                    semantic_group_id=f"{block.doc_id}-P{block.page}-G{counter}-{group_idx}",
                    boundary_reason=reason,
                )
                chunks.append(DocumentChunk(metadata=meta, content=win))
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
