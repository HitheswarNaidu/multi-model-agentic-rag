from typing import List
from rag.generation.llm_client import LLMClient

class QueryExpander:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def expand(self, query: str) -> List[str]:
        prompt = (
            f"You are a helpful assistant. Provide 3 alternative search queries for the following user question. "
            f"Focus on synonyms, domain-specific terms, and related concepts that might appear in a document. "
            f"Return only the 3 queries, one per line.\n\n"
            f"User question: {query}"
        )
        # We reuse the LLM client but with an empty context list as we just want generation
        response = self.llm.generate(contexts=[], query=prompt)
        
        # Parse the 'answer' field which contains the generated text
        text = response.get("answer", "")
        expanded = [line.strip("- ").strip() for line in text.split('\n') if line.strip()]
        return expanded[:3]
