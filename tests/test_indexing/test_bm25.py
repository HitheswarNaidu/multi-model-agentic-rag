from pathlib import Path

from rag.chunking.metadata import ChunkMetadata, DocumentChunk
from rag.indexing.bm25_index import BM25Index


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


def test_bm25_index_and_search(tmp_path: Path):
    ix = BM25Index(tmp_path)
    chunks = [make_chunk(i) for i in range(3)]
    ix.index_documents(chunks)
    results = ix.search("hello", limit=2)
    assert len(results) == 2
    assert all("hello" in r["content"] for r in results)
