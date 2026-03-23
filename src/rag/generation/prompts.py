import datetime


def get_system_rules() -> str:
    today = datetime.date.today().strftime("%Y-%m-%d")
    return (
        f"Current Date: {today}. "
        "Answer based on the provided context. "
        "Cite chunk IDs from the context to support your answer."
    )


def build_prompt(contexts: list[str], query: str, intent: str = "general") -> str:
    context_block = "\n\n".join(contexts)

    intent_hint = ""
    if intent == "summarization":
        intent_hint = "Provide a comprehensive summary covering all key points from the context.\n"
    elif intent == "definition":
        intent_hint = "Give a clear, precise definition or explanation.\n"
    elif intent == "clarification":
        intent_hint = (
            "The query may be vague. Try to answer using the context provided. "
            "If truly unanswerable, suggest what the user might mean.\n"
        )

    return (
        f"System: {get_system_rules()}\n\n"
        f"{intent_hint}"
        f"Context (each prefixed with [chunk_id]):\n{context_block}\n\n"
        f"Question: {query}\n\n"
        "Respond with a JSON object:\n"
        "{\n"
        '  "answer": "your detailed answer here",\n'
        '  "provenance": ["chunk_id_1", "chunk_id_2"],\n'
        '  "conflict": false\n'
        "}\n\n"
        "Important:\n"
        "- Always provide an answer if the context contains ANY relevant information.\n"
        "- provenance = chunk IDs from the context that support your answer.\n"
        "- Only use INSUFFICIENT_DATA if the context is completely empty or "
        "entirely unrelated to the question."
    )
