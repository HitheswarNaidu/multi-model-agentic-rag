from __future__ import annotations

import json
from typing import Dict, List, Optional

from google import genai

from rag.generation.prompts import build_prompt


class LLMClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, contexts: List[str], query: str, intent: str = "general") -> Dict:
        prompt = build_prompt(contexts, query, intent=intent)
        response = self.client.models.generate_content(model=self.model, contents=prompt)
        text = response.text or ""
        try:
            data = json.loads(text)
        except Exception:
            data = {"answer": text.strip(), "provenance": []}
        if "provenance" not in data:
            data["provenance"] = []
        return data


class MockLLMClient(LLMClient):
    def __init__(self, payload: Optional[Dict] = None):
        self.payload = payload or {"answer": "mock", "provenance": []}

    def generate(self, contexts: List[str], query: str, intent: str = "general") -> Dict:
        if "provenance" not in self.payload:
            self.payload["provenance"] = []
        return self.payload
