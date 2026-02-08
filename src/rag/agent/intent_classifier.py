import re
from typing import Literal

IntentType = Literal[
    "numeric_table",
    "definition",
    "multi_hop",
    "image_related",
    "general",
    "clarification",
    "summarization",
]


NUMERIC_PAT = re.compile(r"\b\d|\$|%|\d{1,3},\d{3}")
IMAGE_TERMS = {"image", "figure", "diagram", "chart", "graph", "plot"}
DEFINE_TERMS = {"what is", "define", "meaning of"}
TABLE_TERMS = {"table", "data", "row", "rows", "column", "columns"}
SUMMARIZE_TERMS = {"summarize", "summary", "overview", "tl;dr", "gist"}


def classify_intent(query: str) -> IntentType:
    ql = query.lower()

    if any(term in ql for term in SUMMARIZE_TERMS):
        return "summarization"

    # Single-token queries are usually underspecified.
    if len(ql.split()) < 2:
        return "clarification"

    if any(term in ql for term in IMAGE_TERMS):
        return "image_related"
    # Prioritize explicit table requests
    if any(term in ql for term in TABLE_TERMS):
        return "numeric_table"
    if NUMERIC_PAT.search(ql):
        return "numeric_table"
    if any(term in ql for term in DEFINE_TERMS):
        return "definition"
    if " and " in ql or " as well as " in ql:
        return "multi_hop"
    return "general"
