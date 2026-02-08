from rag.agent.planner import Planner
from rag.generation.llm_client import MockLLMClient


class DummyTools:
    def __init__(self):
        self.bm25 = object()

    def bm25_search(self, query, filters=None, k=5):
        return []

    def vector_search(self, query, filters=None, k=5):
        return []

    def hybrid_search(self, query, filters=None, k=5):
        return []

    def table_row_search(self, query, filters=None, k=5):
        return []


class _FailIfCalled:
    def __getattr__(self, _name):
        raise AssertionError("Helper should not be used in fast mode")


def test_planner_fast_mode_skips_expansion_helpers():
    planner = Planner(DummyTools(), MockLLMClient())
    planner.expander = _FailIfCalled()
    planner.hyde = _FailIfCalled()
    planner.decomposer = _FailIfCalled()

    plan = planner.make_plan("What is RAG?", mode="default")
    results = planner.execute(plan, "What is RAG?", mode="default")
    assert isinstance(results, list)
