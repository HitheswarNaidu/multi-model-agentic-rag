from __future__ import annotations
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name)
            self.enabled = True
        except Exception as e:
            logger.warning(f"Failed to load Reranker model {model_name}: {e}")
            self.enabled = False

    def rerank(self, query: str, documents: List[Dict], top_n: int = 5) -> List[Dict]:
        if not self.enabled or not documents:
            return documents[:top_n]

        # Prepare pairs for cross-encoder: (query, document_content)
        pairs = [[query, doc.get("content", "")] for doc in documents]
        scores = self.model.predict(pairs)

        # Attach scores and sort
        for i, doc in enumerate(documents):
            doc["rerank_score"] = float(scores[i])

        ranked = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
        return ranked[:top_n]
