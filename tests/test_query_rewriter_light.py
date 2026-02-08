from datetime import date

from rag.agent.query_rewriter import QueryRewriter
from rag.generation.llm_client import MockLLMClient


def test_rewrite_light_resolves_last_year():
    rewriter = QueryRewriter(MockLLMClient())
    rewritten = rewriter.rewrite_light(
        "Compare revenue with last year", reference_date=date(2026, 2, 7)
    )
    assert "2025" in rewritten
    assert "last year" not in rewritten.lower()


def test_rewrite_light_resolves_today():
    rewriter = QueryRewriter(MockLLMClient())
    rewritten = rewriter.rewrite_light("What changed today?", reference_date=date(2026, 2, 7))
    assert "2026-02-07" in rewritten
    assert "today" not in rewritten.lower()

