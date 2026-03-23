from __future__ import annotations

import logging
from typing import Any

from rag.config import get_settings

logger = logging.getLogger(__name__)


class Reranker:
    """NVIDIA API-based reranker. No local model downloads required."""

    def __init__(
        self,
        model: str = "nvidia/llama-3.2-nv-rerankqa-1b-v2",
        api_key: str | None = None,
    ):
        self.model_name = model
        self.api_key = api_key or get_settings().nvidia_api_key
        self.enabled = bool(self.api_key)
        self._client: Any | None = None

        if not self.enabled:
            logger.warning("Reranker disabled: NVIDIA_API_KEY not configured")

    def _get_client(self):
        if self._client is None:
            import requests

            self._client = requests.Session()
            self._client.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            })
        return self._client

    def rerank(self, query: str, documents: list[dict], top_n: int = 5) -> list[dict]:
        if not self.enabled or not documents:
            return documents[:top_n]

        try:
            return self._rerank_via_api(query, documents, top_n)
        except Exception as exc:
            logger.warning("NVIDIA reranker failed (%s), returning unranked results", exc)
            return documents[:top_n]

    def _rerank_via_api(self, query: str, documents: list[dict], top_n: int) -> list[dict]:
        client = self._get_client()

        passages = [
            {"text": doc.get("content", "")}
            for doc in documents
        ]

        payload = {
            "model": self.model_name,
            "query": {"text": query},
            "passages": passages,
            "truncate": "END",
        }

        resp = client.post(
            f"https://ai.api.nvidia.com/v1/retrieval/{self.model_name}/reranking",
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        rankings = data.get("rankings", [])
        for entry in rankings:
            idx = entry.get("index", 0)
            score = entry.get("logit", 0.0)
            if 0 <= idx < len(documents):
                documents[idx]["rerank_score"] = float(score)

        ranked = sorted(documents, key=lambda x: x.get("rerank_score", -999), reverse=True)
        return ranked[:top_n]
