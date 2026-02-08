from __future__ import annotations

import json
import re

from google import genai

from rag.generation.prompts import build_prompt


class LLMClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model

    @staticmethod
    def _extract_json_payload(text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            return "{}"
        fence = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", raw, flags=re.IGNORECASE)
        if fence:
            return fence.group(1).strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return raw[start : end + 1].strip()
        return raw

    def generate(self, contexts: list[str], query: str, intent: str = "general") -> dict:
        prompt = build_prompt(contexts, query, intent=intent)
        response = self.client.models.generate_content(model=self.model, contents=prompt)
        text = response.text or ""
        parsed_text = self._extract_json_payload(text)
        try:
            data = json.loads(parsed_text)
        except Exception:
            data = {
                "answer": text.strip(),
                "provenance": [],
                "conflict": False,
                "error": {
                    "code": "LLM_RESPONSE_PARSE_FAILED",
                    "message": "Model response was not valid JSON.",
                },
            }
        if not isinstance(data, dict):
            data = {"answer": str(data), "provenance": []}
        if "answer" not in data:
            data["answer"] = ""
        if "provenance" not in data:
            data["provenance"] = []
        if not isinstance(data["provenance"], list):
            data["provenance"] = []
        if "conflict" not in data:
            data["conflict"] = False
        return data


class MockLLMClient(LLMClient):
    def __init__(self, payload: dict | None = None):
        self.payload = payload or {"answer": "mock", "provenance": []}

    def generate(self, contexts: list[str], query: str, intent: str = "general") -> dict:
        if "provenance" not in self.payload:
            self.payload["provenance"] = []
        return self.payload
