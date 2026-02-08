from unittest.mock import MagicMock

from rag.pipeline import Pipeline


def test_update_retriever_weights():
    p = Pipeline()
    # Mock hybrid retriever
    p.hybrid = MagicMock()
    p.hybrid.weight_bm25 = 0.5
    p.hybrid.weight_vector = 0.5
    p._runtime_ready = True

    p.update_retriever_weights(0.8, 0.2)

    assert p.hybrid.weight_bm25 == 0.8
    assert p.hybrid.weight_vector == 0.2

def test_ingest_passes_chunk_params(tmp_path, monkeypatch):
    # Mock dependencies to avoid real IO
    monkeypatch.setattr("rag.pipeline.iter_documents", lambda x: [tmp_path / "test.txt"])
    monkeypatch.setattr(
        "rag.pipeline.parse_document",
        lambda path, settings=None: MagicMock(blocks=[]),
    )

    mock_chunker = MagicMock(return_value=[])
    monkeypatch.setattr("rag.pipeline.chunk_blocks", mock_chunker)

    p = Pipeline()
    p.ingest_uploads(chunk_size=123, chunk_overlap=45)

    # Verify our custom params were passed to chunker
    call_kwargs = mock_chunker.call_args[1]
    assert call_kwargs["max_chars"] == 123
    assert call_kwargs["overlap"] == 45
