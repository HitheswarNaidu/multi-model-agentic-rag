from unittest.mock import MagicMock, patch

from rag.indexing.reranker import Reranker


def test_reranker_disabled_without_key():
    """Reranker gracefully disables when no API key is set."""
    reranker = Reranker(api_key="")
    assert not reranker.enabled

    docs = [{"content": "a"}, {"content": "b"}]
    results = reranker.rerank("query", docs, top_n=2)
    assert results == docs


def test_reranker_disabled_returns_truncated():
    reranker = Reranker(api_key="")
    docs = [{"content": "a"}, {"content": "b"}, {"content": "c"}]
    results = reranker.rerank("query", docs, top_n=1)
    assert len(results) == 1


def test_reranker_api_call():
    """Test that reranker calls NVIDIA API and sorts by logit scores."""
    reranker = Reranker(api_key="nvapi-test")
    assert reranker.enabled

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "rankings": [
            {"index": 0, "logit": 1.5},
            {"index": 1, "logit": 8.2},
            {"index": 2, "logit": 0.3},
        ]
    }

    docs = [
        {"content": "Paris is the capital of France.", "id": "1"},
        {"content": "France's capital is Paris.", "id": "2"},
        {"content": "Berlin is in Germany.", "id": "3"},
    ]

    with patch.object(reranker, "_get_client") as mock_client:
        mock_client.return_value.post.return_value = mock_response
        results = reranker.rerank("What is the capital of France?", docs, top_n=2)

    assert len(results) == 2
    # doc at index 1 had highest logit (8.2), should be first
    assert results[0]["id"] == "2"
    assert results[0]["rerank_score"] == 8.2
    assert results[1]["id"] == "1"


def test_reranker_api_failure_returns_unranked():
    """If API fails, return original docs truncated."""
    reranker = Reranker(api_key="nvapi-test")

    with patch.object(reranker, "_get_client") as mock_client:
        mock_client.return_value.post.side_effect = Exception("API timeout")
        docs = [{"content": "a"}, {"content": "b"}]
        results = reranker.rerank("query", docs, top_n=2)

    assert len(results) == 2
    assert results[0]["content"] == "a"  # Unchanged order
