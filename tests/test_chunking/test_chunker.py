from rag.chunking.chunker import chunk_blocks
from rag.ingestion.parser import Block


def test_chunk_blocks_basic():
    blocks = [
        Block(doc_id="d1", page=1, chunk_type="paragraph", text="Hello world", confidence=0.9),
    ]
    chunks = chunk_blocks(blocks, doc_type="pdf", max_chars=50, overlap=10)
    assert len(chunks) == 1
    c = chunks[0]
    assert c.metadata.doc_id == "d1"
    assert c.metadata.page == 1
    assert c.content == "Hello world"


def test_chunk_blocks_windows():
    text = "This is a longer text that should be split into multiple windows for testing purposes."
    blocks = [Block(doc_id="d1", page=1, chunk_type="paragraph", text=text, confidence=0.9)]
    chunks = chunk_blocks(blocks, doc_type="pdf", max_chars=30, overlap=5)
    assert len(chunks) > 1
    # Ensure overlap allowed and all non-empty
    assert all(len(c.content) > 0 for c in chunks)
