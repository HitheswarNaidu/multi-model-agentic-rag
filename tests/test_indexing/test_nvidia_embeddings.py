from unittest.mock import MagicMock, patch

from rag.indexing.vector_store import HashEmbeddingFunction, NVIDIAEmbeddingFunction


def test_hash_embedding_unchanged():
    fn = HashEmbeddingFunction(dimension=64)
    result = fn(["hello", "world"])
    assert len(result) == 2
    assert len(result[0]) == 64


@patch("langchain_nvidia_ai_endpoints.NVIDIAEmbeddings")
def test_nvidia_embedding_calls_embed_documents(mock_cls):
    mock_instance = MagicMock()
    mock_instance.embed_documents.return_value = [[0.1] * 2048, [0.2] * 2048]
    mock_cls.return_value = mock_instance

    fn = NVIDIAEmbeddingFunction(
        model_name="nvidia/llama-nemotron-embed-1b-v2",
        api_key="nvapi-test",
    )
    result = fn(["hello", "world"])
    assert len(result) == 2
    assert len(result[0]) == 2048
    mock_instance.embed_documents.assert_called_once_with(["hello", "world"])


def test_nvidia_embedding_lazy_init():
    fn = NVIDIAEmbeddingFunction(model_name="test-model", api_key="test-key")
    assert fn._embedder is None


def test_vector_store_uses_hash_for_test():
    from rag.indexing.vector_store import VectorStore

    vs = VectorStore(embedding_model="hash-embedding")
    assert isinstance(vs.embedding_fn, HashEmbeddingFunction)
