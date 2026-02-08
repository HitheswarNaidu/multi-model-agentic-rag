from pathlib import Path

import chromadb

from rag.chunking.metadata import ChunkMetadata, DocumentChunk
from rag.indexing.vector_store import VectorStore


def make_chunk(idx: int, doc_id: str = "doc1") -> DocumentChunk:
    meta = ChunkMetadata(
        doc_id=doc_id,
        doc_type="pdf",
        page=1,
        section="s",
        chunk_id=f"c{idx}",
        chunk_type="paragraph",
        table_id=None,
        confidence=0.9,
    )
    return DocumentChunk(metadata=meta, content=f"hello world {idx}")


def test_vector_store_index_and_search(tmp_path: Path):
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma_a"))
    collection = client.create_collection("test", metadata={"hnsw:space": "cosine"})

    # Monkeypatch embedding to avoid heavy model load
    class DummyEmbeddingFn:
        def __call__(self, input):
            # deterministic small vectors
            return [[float(i)] * 2 for i, _ in enumerate(input)]

    vs = VectorStore(
        collection_name="test",
        client=client,
        embedding_fn=DummyEmbeddingFn(),
        collection=collection,
    )
    chunks = [make_chunk(i) for i in range(3)]
    vs.index_documents(chunks)
    results = vs.search("hello", limit=2)
    assert len(results) == 2
    assert all(r["chunk_id"].startswith("c") for r in results)


def test_vector_store_batched_upsert_metrics(tmp_path: Path):
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma_b"))
    collection = client.create_collection("test_metrics", metadata={"hnsw:space": "cosine"})

    class DummyEmbeddingFn:
        def __call__(self, input):
            return [[float(i)] * 2 for i, _ in enumerate(input)]

    vs = VectorStore(
        collection_name="test_metrics",
        client=client,
        embedding_fn=DummyEmbeddingFn(),
        collection=collection,
    )
    chunks = [make_chunk(i) for i in range(5)]
    metrics = vs.index_documents_batched(chunks, batch_size=2)

    assert metrics["indexed"] == 5
    assert metrics["upsert_batches"] == 3
    assert metrics["embed_ms"] >= 0.0
    assert metrics["upsert_ms"] >= 0.0


def test_vector_store_filter_doc_ids(tmp_path: Path):
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma_c"))
    collection = client.create_collection("test_filter", metadata={"hnsw:space": "cosine"})

    class DummyEmbeddingFn:
        def __call__(self, input):
            return [[float(i)] * 2 for i, _ in enumerate(input)]

    vs = VectorStore(
        collection_name="test_filter",
        client=client,
        embedding_fn=DummyEmbeddingFn(),
        collection=collection,
    )
    vs.index_documents([make_chunk(1, "doc1"), make_chunk(2, "doc2")])
    results = vs.search("hello", limit=10, filters={"doc_ids": ["doc2"]})
    assert len(results) == 1
    assert results[0]["metadata"]["doc_id"] == "doc2"
