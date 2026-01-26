from rag.indexing.bm25_index import BM25Index
from rag.indexing.hybrid_retriever import HybridRetriever
from rag.indexing.vector_store import VectorStore
from rag.chunking.metadata import ChunkMetadata, DocumentChunk


def make_chunk(idx: int, content: str) -> DocumentChunk:
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
    return DocumentChunk(metadata=meta, content=content)


def test_hybrid_rrf_combines(monkeypatch, tmp_path):
    # Dummy BM25
    bm25 = BM25Index(tmp_path / "bm25")
    vec_collection = None

    class DummyVec(VectorStore):
        def __init__(self):
            self.calls = 0

        def search(self, query, limit=5, doc_type=None):
            self.calls += 1
            return [
                {"chunk_id": "c2", "content": "vector match", "score": 0.9, "metadata": {}},
            ]

    dummy_vec = DummyVec()
    # Seed bm25 with a simple writer
    bm25.index_documents([make_chunk(1, "hello world"), make_chunk(2, "another entry")])
    retriever = HybridRetriever(bm25=bm25, vector=dummy_vec, weight_bm25=0.6, weight_vector=0.4)
    results = retriever.search("hello", limit=2)
    assert len(results) >= 1
    # ensure hybrid_score present
    assert all("hybrid_score" in r for r in results)
