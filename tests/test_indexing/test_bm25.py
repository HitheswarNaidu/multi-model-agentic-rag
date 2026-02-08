from pathlib import Path

from rag.chunking.metadata import ChunkMetadata, DocumentChunk
from rag.indexing.bm25_index import BM25Index


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


def test_bm25_index_and_search(tmp_path: Path):
    ix = BM25Index(tmp_path)
    chunks = [make_chunk(i) for i in range(3)]
    ix.index_documents(chunks)
    results = ix.search("hello", limit=2)
    assert len(results) == 2
    assert all("hello" in r["content"] for r in results)


def test_bm25_batch_writer_lifecycle(tmp_path: Path):
    ix = BM25Index(tmp_path)
    chunks = [make_chunk(i) for i in range(4)]
    writer = ix.open_writer()
    wrote = ix.add_documents_to_writer(writer, chunks[:2])
    assert wrote == 2
    wrote += ix.add_documents_to_writer(writer, chunks[2:])
    assert wrote == 4
    ix.commit_writer(writer)

    results = ix.search("world", limit=4)
    assert len(results) == 4


def test_bm25_filter_doc_ids(tmp_path: Path):
    ix = BM25Index(tmp_path)
    ix.index_documents([make_chunk(1, "doc1"), make_chunk(2, "doc2")])
    results = ix.search("hello", limit=10, filters={"doc_ids": ["doc2"]})
    assert len(results) == 1
    assert results[0]["doc_id"] == "doc2"
