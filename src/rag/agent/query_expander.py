from rag.generation.llm_client import LLMClient


class QueryExpander:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def expand(self, query: str) -> list[str]:
        prompt = (
            "You are a helpful assistant. Provide 3 alternative search queries "
            "for the following user question. "
            "Focus on synonyms, domain-specific terms, and related concepts "
            "that might appear in a document. "
            f"Return only the 3 queries, one per line.\n\n"
            f"User question: {query}"
        )
        # We reuse the LLM client but with an empty context list as we just want generation
        text = self.llm.call_raw(prompt)
        expanded = [line.strip("- ").strip() for line in text.split("\n") if line.strip()]
        return expanded[:3]
