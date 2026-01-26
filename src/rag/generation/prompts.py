from typing import List

SYSTEM_RULES = (
    "Use only provided context; do not fabricate facts. "
    "Always include provenance ids for claims. "
    "If insufficient evidence, respond with INSUFFICIENT_DATA."
)


def build_prompt(contexts: List[str], query: str, intent: str = "general") -> str:
    context_block = "\n\n".join(contexts)
    
    special_instr = ""
    if intent == "clarification":
        special_instr = (
            "NOTE: The user's query is vague. "
            "Using the provided context (if any), suggest a clarification question or a better scope. "
            "Do not try to answer definitively if you are unsure."
        )

    return (
        f"System: {SYSTEM_RULES}\n"
        f"{special_instr}\n"
        f"Context:\n{context_block}\n\n"
        f"User question: {query}\n"
        "Return a valid JSON object with this exact structure:\n"
        "{\n"
        "  \"answer\": \"your text answer\",\n"
        "  \"provenance\": [\"chunk_id_1\", \"chunk_id_2\"],\n"
        "  \"conflict\": false\n"
        "}\n"
        "Set 'conflict' to true if different context chunks provide contradicting information."
    )
