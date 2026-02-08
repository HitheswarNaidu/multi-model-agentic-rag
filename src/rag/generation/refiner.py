from rag.generation.llm_client import LLMClient


class Refiner:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def refine_answer(self, query: str, context: list[str], draft_answer: str) -> dict:
        """
        Critique and refine the answer to ensure it is fully supported by context.
        """
        context_block = "\n\n".join(context)
        prompt = (
            "You are a strict fact-checker. "
            "Review the following Draft Answer against the Context.\n"
            "1. If the Draft Answer contains facts NOT present in the Context, "
            "remove or correct them.\n"
            f"2. If the Draft Answer is fully supported, return it as is.\n"
            f"3. Ensure the tone is professional.\n\n"
            f"Context:\n{context_block}\n\n"
            f"User Question: {query}\n"
            f"Draft Answer: {draft_answer}\n\n"
            f"Return a JSON object with:\n"
            f"{{ \"refined_answer\": \"...\", \"corrections_made\": boolean }}"
        )

        response = self.llm.generate(contexts=[], query=prompt)

        # Fallback if LLM doesn't follow JSON structure
        if "answer" in response:
            # If the LLM returned a standard answer structure instead of our custom JSON,
            # assume the 'answer' text is the refined output.
            return {
                "refined_answer": response["answer"],
                "corrections_made": True,
            }

        return {
            "refined_answer": response.get("refined_answer", draft_answer),
            "corrections_made": response.get("corrections_made", False),
        }
