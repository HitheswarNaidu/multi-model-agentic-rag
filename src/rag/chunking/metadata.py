from dataclasses import dataclass
from typing import Literal, Optional


ChunkType = Literal["paragraph", "table", "row", "figure"]


@dataclass
class ChunkMetadata:
    doc_id: str
    doc_type: str
    page: int
    section: str
    chunk_id: str
    chunk_type: ChunkType
    table_id: Optional[str]
    confidence: float


@dataclass
class DocumentChunk:
    metadata: ChunkMetadata
    content: str
