from __future__ import annotations

import json
import logging
import re

from rag.generation.prompts import build_prompt

logger = logging.getLogger(__name__)


class RateLimitError(RuntimeError):
    code = "LLM_RATE_LIMITED"


class LLMQuotaExhaustedError(RuntimeError):
    code = "LLM_QUOTA_EXHAUSTED"


class LLMClient:
    def __init__(
        self,
        groq_api_key: str = "",
        openrouter_api_key: str = "",
        fallback_chain: str = "",
    ) -> None:
        self.groq_api_key = groq_api_key
        self.openrouter_api_key = openrouter_api_key
        self.chain = self._parse_chain(fallback_chain)

    @staticmethod
    def _parse_chain(chain_str: str) -> list[tuple[str, str]]:
        result = []
        for entry in chain_str.split(","):
            entry = entry.strip()
            if ":" not in entry:
                continue
            provider, _, model = entry.partition(":")
            if provider.strip() and model.strip():
                result.append((provider.strip(), model.strip()))
        return result

    def _build_groq(self, model: str):
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=model, api_key=self.groq_api_key, temperature=0.1, max_tokens=1024
        )

    def _build_openrouter(self, model: str):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=self.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.1,
            max_tokens=1024,
            default_headers={
                "HTTP-Referer": "https://multimodal-agentic-rag.app",
                "X-Title": "Multimodal Agentic RAG",
            },
        )

    def _call_provider(self, provider: str, model: str, prompt: str) -> dict:
        if provider == "groq":
            llm = self._build_groq(model)
        elif provider == "openrouter":
            llm = self._build_openrouter(model)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

        try:
            response = llm.invoke(prompt)
        except Exception as exc:
            error_text = str(exc).lower()
            if "429" in error_text or "rate" in error_text or "quota" in error_text:
                raise RateLimitError(str(exc)) from exc
            raise

        text = response.content if hasattr(response, "content") else str(response)
        return self._parse_response(text)

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

    def _parse_response(self, text: str) -> dict:
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

    def generate(self, contexts: list[str], query: str, intent: str = "general") -> dict:
        prompt = build_prompt(contexts, query, intent=intent)

        for idx, (provider, model) in enumerate(self.chain):
            try:
                result = self._call_provider(provider, model, prompt)
                result["_llm_provider"] = provider
                result["_llm_model"] = model
                result["_llm_fallback_used"] = idx > 0
                return result
            except RateLimitError:
                logger.warning(
                    "Rate limited by %s:%s, trying next in chain", provider, model
                )
                continue

        raise LLMQuotaExhaustedError(
            "All LLM providers in the fallback chain are exhausted. "
            "Configure additional providers or wait for rate limits to reset."
        )


class MockLLMClient(LLMClient):
    def __init__(self, payload: dict | None = None):
        self.payload = payload or {"answer": "mock", "provenance": []}
        self.chain = []

    def generate(self, contexts: list[str], query: str, intent: str = "general") -> dict:
        if "provenance" not in self.payload:
            self.payload["provenance"] = []
        return self.payload
