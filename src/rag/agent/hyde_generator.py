from rag.generation.llm_client import LLMClient


class HydeGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def generate_hypothetical_document(self, query: str) -> str:
        prompt = (
            f"Please write a short, hypothetical passage that answers the following question. "
            f"Include keywords and factual patterns expected in a relevant document. "
            f"Do not include preamble or conversational filler. Just the passage.\n\n"
            f"Question: {query}\n\n"
            f"Hypothetical Passage:"
        )

        response = self.llm.generate(contexts=[], query=prompt)
        text = response.get("answer", "").strip()
        return text
