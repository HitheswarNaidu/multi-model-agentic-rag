from __future__ import annotations

from rag.indexing.bm25_index import BM25Index


class Summarizer:
    def __init__(self, bm25: BM25Index):
        self.bm25 = bm25

    def gather_document_chunks(self, doc_id: str, limit: int = 64) -> list[dict]:
        # Retrieve broad evidence from one document and preserve narrative order.
        results = self.bm25.get_chunks_by_doc_id(doc_id=doc_id, limit=max(1, int(limit)))
        if not results:
            results = self.bm25.search(doc_id, doc_id=doc_id, limit=max(1, int(limit)))

        def sort_key(item: dict) -> tuple[int, int]:
            raw_id = str(item.get("chunk_id", ""))
            page = int(item.get("metadata", {}).get("page", item.get("page", 0)) or 0)
            chunk_num = 0
            try:
                tail = raw_id.rsplit("-", 1)[-1]
                digits = "".join(ch for ch in tail if ch.isdigit())
                chunk_num = int(digits) if digits else 0
            except Exception:
                chunk_num = 0
            return (page, chunk_num)

        return sorted(results, key=sort_key)
