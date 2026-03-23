from rag.generation.llm_client import LLMClient


class Decomposer:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def decompose(self, query: str) -> list[str]:
        prompt = (
            "You are a reasoning assistant. "
            "Decompose the following complex user query into exactly 2 simpler "
            "sub-questions that need to be answered sequentially or independently "
            "to satisfy the original request.\n\n"
            f"User query: {query}\n\n"
            f"Sub-questions (return 1 per line):"
        )

        text = self.llm.call_raw(prompt)
        questions = [
            line.strip("- ").strip()
            for line in text.split("\n")
            if line.strip() and "?" in line
        ]

        # Ensure we have at least the original if decomposition fails
        if not questions:
            return [query]
        return questions[:2]
