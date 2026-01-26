import pytest
from rag.indexing.reranker import Reranker

def test_reranker_basic():
    # Mocking the model to avoid heavy download during test if possible
    # But since we can't easily mock CrossEncoder without more boilerplate,
    # we'll test the logic with a mocked model if needed.
    
    reranker = Reranker()
    # If model failed to load (no internet/etc), it should still not crash
    
    query = "What is the capital of France?"
    docs = [
        {"content": "Paris is the capital of France.", "id": "1"},
        {"content": "The cat sat on the mat.", "id": "2"},
        {"content": "Berlin is in Germany.", "id": "3"}
    ]
    
    results = reranker.rerank(query, docs, top_n=2)
    assert len(results) <= 2
    if reranker.enabled:
        assert results[0]["id"] == "1"
        assert "rerank_score" in results[0]

def test_reranker_disabled():
    reranker = Reranker()
    reranker.enabled = False
    docs = [{"content": "a"}, {"content": "b"}]
    res = reranker.rerank("q", docs)
    assert res == docs
