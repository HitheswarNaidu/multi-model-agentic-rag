from dataclasses import dataclass
from typing import Literal

ChunkType = Literal["paragraph", "table", "row", "figure", "image_text"]


@dataclass
class ChunkMetadata:
    doc_id: str
    doc_type: str
    page: int
    section: str
    chunk_id: str
    chunk_type: ChunkType
    table_id: str | None
    confidence: float
    parent_content: str | None = None  # Larger context for hierarchical retrieval
    source_path: str | None = None
    source_hash: str | None = None
    ingest_timestamp_utc: str | None = None
    is_table: bool = False
    is_image: bool = False
    semantic_group_id: str | None = None
    boundary_reason: str | None = None


@dataclass
class DocumentChunk:
    metadata: ChunkMetadata
    content: str
