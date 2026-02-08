from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model: Any | None = None
        self.enabled = False
        try:
            from sentence_transformers import CrossEncoder

            # Some torch/transformers combinations initialize modules on meta tensors.
            # Force a CPU-first, non-meta path before any optional device moves.
            load_attempts = [
                {"device": "cpu", "automodel_args": {"low_cpu_mem_usage": False}},
                {"device": "cpu"},
                {},
            ]
            last_error: Exception | None = None
            for kwargs in load_attempts:
                try:
                    self.model = CrossEncoder(model_name, **kwargs)
                    self.enabled = True
                    break
                except Exception as exc:  # pragma: no cover - depends on local HF/torch stack
                    last_error = exc

            if not self.enabled:
                logger.warning(f"Failed to load Reranker model {model_name}: {last_error}")
        except Exception as e:
            logger.warning(f"Failed to load Reranker model {model_name}: {e}")
            self.enabled = False

    def rerank(self, query: str, documents: list[dict], top_n: int = 5) -> list[dict]:
        if not self.enabled or self.model is None or not documents:
            return documents[:top_n]

        # Prepare pairs for cross-encoder: (query, document_content)
        pairs = [[query, doc.get("content", "")] for doc in documents]
        scores = self.model.predict(pairs)

        # Attach scores and sort
        for i, doc in enumerate(documents):
            doc["rerank_score"] = float(scores[i])

        ranked = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
        return ranked[:top_n]
