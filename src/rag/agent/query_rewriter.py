import datetime
import re

from rag.agent.memory import ConversationMemory
from rag.generation.llm_client import LLMClient


class QueryRewriter:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def rewrite_light(self, query: str, reference_date: datetime.date | None = None) -> str:
        """Deterministic rewrite for fast mode: resolve relative temporal phrases only."""
        today = reference_date or datetime.date.today()
        replacements = [
            (r"\blast year\b", str(today.year - 1)),
            (r"\bthis year\b", str(today.year)),
            (r"\bnext year\b", str(today.year + 1)),
            (r"\byesterday\b", (today - datetime.timedelta(days=1)).isoformat()),
            (r"\btoday\b", today.isoformat()),
            (r"\btomorrow\b", (today + datetime.timedelta(days=1)).isoformat()),
        ]
        rewritten = query
        for pattern, replacement in replacements:
            rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)
        return rewritten

    def rewrite(
        self,
        query: str,
        memory: ConversationMemory,
        mode: str = "deep",
        deep_enabled: bool = True,
    ) -> str:
        if mode != "deep" or not deep_enabled:
            return self.rewrite_light(query)

        history = memory.get_history_string()
        # Even if history is empty, we might want to resolve "last year" relative to today.
        # But usually rewriter is for context.
        # Let's include date anyway.

        today = datetime.date.today().strftime("%Y-%m-%d")

        prompt = (
            f"Current Date: {today}\n"
            "Given the following conversation history (if any), rewrite the last "
            "user input to be a standalone question that includes all necessary "
            "context and resolves relative dates (e.g. 'last year') to "
            "specific years.\n"
            f"If the input is already self-contained, return it unchanged.\n"
            f"Do NOT answer the question, just rewrite it.\n\n"
            f"History:\n{history}\n\n"
            f"Last User Input: {query}\n\n"
            f"Rewritten Input:"
        )

        rewritten = self.llm.call_raw(prompt).strip()
        # Strip quotes/markdown the LLM may wrap around the rewrite
        rewritten = rewritten.strip('"\'`')
        # If the LLM returned garbage, JSON, or INSUFFICIENT_DATA, use original
        if not rewritten or "INSUFFICIENT" in rewritten or rewritten.startswith("{"):
            return query
        return rewritten
