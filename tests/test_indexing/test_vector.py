from pathlib import Path

import chromadb

from rag.chunking.metadata import ChunkMetadata, DocumentChunk
from rag.indexing.vector_store import VectorStore


def make_chunk(idx: int) -> DocumentChunk:
    meta = ChunkMetadata(
        doc_id="doc1",
        doc_type="pdf",
        page=1,
        section="s",
        chunk_id=f"c{idx}",
        chunk_type="paragraph",
        table_id=None,
        confidence=0.9,
    )
    return DocumentChunk(metadata=meta, content=f"hello world {idx}")


def test_vector_store_index_and_search(tmp_path: Path, monkeypatch):
    client = chromadb.Client(settings=chromadb.config.Settings(anonymized_telemetry=False))
    collection = client.create_collection("test", metadata={"hnsw:space": "cosine"})

    # Monkeypatch embedding to avoid heavy model load
    class DummyEmbeddingFn:
        def __call__(self, input):
            # deterministic small vectors
            return [[float(i)] * 2 for i, _ in enumerate(input)]

    vs = VectorStore(collection_name="test", client=client, embedding_fn=DummyEmbeddingFn(), collection=collection)
    chunks = [make_chunk(i) for i in range(3)]
    vs.index_documents(chunks)
    results = vs.search("hello", limit=2)
    assert len(results) == 2
    assert all(r["chunk_id"].startswith("c") for r in results)
