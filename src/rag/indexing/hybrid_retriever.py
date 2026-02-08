from __future__ import annotations

from rag.indexing.bm25_index import BM25Index
from rag.indexing.reranker import Reranker
from rag.indexing.vector_store import VectorStore


def _rrf(scores: list[dict], k: int = 60) -> dict[str, float]:
    out: dict[str, float] = {}
    for rank, item in enumerate(scores, start=1):
        cid = item["chunk_id"]
        out[cid] = out.get(cid, 0.0) + 1.0 / (k + rank)
    return out


class HybridRetriever:
    def __init__(
        self,
        bm25: BM25Index,
        vector: VectorStore,
        weight_bm25: float = 0.6,
        weight_vector: float = 0.4,
        enable_reranker: bool = False,
    ) -> None:
        self.bm25 = bm25
        self.vector = vector
        self.weight_bm25 = weight_bm25
        self.weight_vector = weight_vector
        self.reranker = Reranker() if enable_reranker else None

    def set_reranker_enabled(self, enabled: bool) -> None:
        if enabled and self.reranker is None:
            self.reranker = Reranker()
        if not enabled:
            self.reranker = None

    @staticmethod
    def _safe_search(
        backend,
        query: str,
        limit: int,
        filters: dict | None,
        doc_type: str | None,
        doc_id: str | None,
        chunk_type: str | None,
    ) -> list[dict]:
        """Call backend.search across old/new signatures."""
        filters = filters or {}
        search_fn = getattr(backend, "search")
        attempts = [
            lambda: search_fn(query, limit=limit, filters=filters),
            lambda: search_fn(
                query,
                limit=limit,
                doc_type=doc_type,
                doc_id=doc_id,
                chunk_type=chunk_type,
            ),
            lambda: search_fn(query, limit=limit, doc_type=doc_type),
            lambda: search_fn(query, limit=limit),
            lambda: search_fn(query),
        ]
        for attempt in attempts:
            try:
                return attempt() or []
            except TypeError:
                continue
        return []

    def search(
        self,
        query: str,
        limit: int = 5,
        filters: dict | None = None,
        doc_type: str | None = None,
        doc_id: str | None = None,
        chunk_type: str | None = None,
    ) -> list[dict]:
        f = filters or {}
        doc_type = f.get("doc_type", doc_type)
        doc_id = f.get("doc_id", doc_id)
        chunk_type = f.get("chunk_type", chunk_type)
        expand_semantic_context = bool(f.get("expand_semantic_context", False))

        # Increase initial k for hybrid fusion to give reranker more candidates
        fetch_limit = limit * 3 if self.reranker else limit

        bm25_results = self._safe_search(
            self.bm25, query, fetch_limit, f, doc_type, doc_id, chunk_type
        )
        vec_results = self._safe_search(
            self.vector, query, fetch_limit, f, doc_type, doc_id, chunk_type
        )

        scores: dict[str, float] = {}
        combined: dict[str, dict] = {}

        bm25_rrf = _rrf(bm25_results)
        vec_rrf = _rrf(vec_results)

        for item in bm25_results:
            cid = item["chunk_id"]
            combined[cid] = item
            scores[cid] = scores.get(cid, 0.0) + self.weight_bm25 * bm25_rrf.get(cid, 0.0)

        for item in vec_results:
            cid = item["chunk_id"]
            if cid not in combined:
                combined[cid] = item
            scores[cid] = scores.get(cid, 0.0) + self.weight_vector * vec_rrf.get(cid, 0.0)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_candidates: list[dict] = []
        for cid, score in ranked[:fetch_limit]:
            entry = combined[cid].copy()
            entry["hybrid_score"] = score

            # Parent retrieval: if parent_content exists, promote it to context content.
            # Check metadata first (from Vector)
            meta = entry.get("metadata", {})
            if isinstance(meta, dict) and meta.get("parent_content"):
                entry["content"] = meta["parent_content"]
                entry["is_parent_expanded"] = True
            # Check direct field (from BM25)
            elif entry.get("parent_content"):
                entry["content"] = entry["parent_content"]
                entry["is_parent_expanded"] = True

            top_candidates.append(entry)

        if self.reranker and top_candidates:
            reranked = self.reranker.rerank(query, top_candidates, top_n=limit)
            if expand_semantic_context:
                return self._expand_semantic_context(reranked)
            return reranked

        selected = top_candidates[:limit]
        if expand_semantic_context:
            return self._expand_semantic_context(selected)
        return selected

    @staticmethod
    def _expand_semantic_context(results: list[dict]) -> list[dict]:
        if not results:
            return results
        grouped: dict[str, list[str]] = {}
        for item in results:
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict):
                continue
            group_id = str(metadata.get("semantic_group_id", "") or "")
            content = str(item.get("content", "") or "")
            if not group_id or not content:
                continue
            grouped.setdefault(group_id, [])
            grouped[group_id].append(content)

        if not grouped:
            return results

        enriched: list[dict] = []
        for item in results:
            updated = item.copy()
            metadata = updated.get("metadata", {})
            if isinstance(metadata, dict):
                group_id = str(metadata.get("semantic_group_id", "") or "")
                group_texts = grouped.get(group_id, [])
                if group_texts:
                    updated["content"] = "\n".join(dict.fromkeys(group_texts))
                    updated["is_semantic_expanded"] = True
            enriched.append(updated)
        return enriched
