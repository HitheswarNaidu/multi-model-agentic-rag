from __future__ import annotations

from typing import Dict, List, Optional

from rag.indexing.bm25_index import BM25Index
from rag.indexing.vector_store import VectorStore
from rag.indexing.reranker import Reranker


def _rrf(scores: List[dict], k: int = 60) -> Dict[str, float]:
    out: Dict[str, float] = {}
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
        use_reranker: bool = True,
    ) -> None:
        self.bm25 = bm25
        self.vector = vector
        self.weight_bm25 = weight_bm25
        self.weight_vector = weight_vector
        self.reranker = Reranker() if use_reranker else None

    def search(
        self,
        query: str,
        limit: int = 5,
        doc_type: Optional[str] = None,
        doc_id: Optional[str] = None,
        chunk_type: Optional[str] = None,
    ) -> List[dict]:
        # Increase initial k for hybrid fusion to give reranker more candidates
        fetch_limit = limit * 3 if self.reranker else limit
        
        bm25_results = self.bm25.search(
            query, limit=fetch_limit, doc_type=doc_type, doc_id=doc_id, chunk_type=chunk_type
        )
        vec_results = self.vector.search(
            query, limit=fetch_limit, doc_type=doc_type, doc_id=doc_id, chunk_type=chunk_type
        )

        scores: Dict[str, float] = {}
        combined: Dict[str, dict] = {}

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
        top_candidates: List[dict] = []
        for cid, score in ranked[:fetch_limit]:
            entry = combined[cid].copy()
            entry["hybrid_score"] = score
            top_candidates.append(entry)
            
        if self.reranker and top_candidates:
            return self.reranker.rerank(query, top_candidates, top_n=limit)
            
        return top_candidates[:limit]
