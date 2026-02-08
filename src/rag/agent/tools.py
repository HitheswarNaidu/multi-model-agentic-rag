from __future__ import annotations

from rag.indexing.bm25_index import BM25Index
from rag.indexing.hybrid_retriever import HybridRetriever
from rag.indexing.vector_store import VectorStore


class AgentTools:
    def __init__(self, bm25: BM25Index, vector: VectorStore, hybrid: HybridRetriever):
        self.bm25 = bm25
        self.vector = vector
        self.hybrid = hybrid

    def bm25_search(self, query: str, filters: dict | None = None, k: int = 5) -> list[dict]:
        f = filters or {}
        return self.bm25.search(query, limit=k, filters=f)

    def vector_search(self, query: str, filters: dict | None = None, k: int = 5) -> list[dict]:
        f = filters or {}
        return self.vector.search(query, limit=k, filters=f)

    def hybrid_search(self, query: str, filters: dict | None = None, k: int = 5) -> list[dict]:
        f = filters or {}
        return self.hybrid.search(query, limit=k, filters=f)

    def table_row_search(self, query: str, filters: dict | None = None, k: int = 5) -> list[dict]:
        f = (filters or {}).copy()
        f["chunk_type"] = "row"
        return self.hybrid_search(query, filters=f, k=k)
