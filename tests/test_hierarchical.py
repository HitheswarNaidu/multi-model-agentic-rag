from rag.chunking.chunker import chunk_blocks
from rag.ingestion.parser import Block


def test_hierarchical_chunking_enabled():
    text = "A" * 2000 # Long text
    blocks = [Block(doc_id="d1", page=1, chunk_type="paragraph", text=text, confidence=1.0)]

    # 400 chars child, 1200 chars parent
    chunks = chunk_blocks(blocks, "txt", max_chars=400, overlap=0, enable_hierarchy=True)

    assert len(chunks) > 0
    # Check if parent_content is present
    has_parent = any(c.metadata.parent_content for c in chunks)
    assert has_parent

    # Verify child size
    assert len(chunks[0].content) <= 400
    # Verify parent size
    if chunks[0].metadata.parent_content:
        assert len(chunks[0].metadata.parent_content) > 400

def test_hierarchical_chunking_disabled():
    text = "A" * 1000
    blocks = [Block(doc_id="d1", page=1, chunk_type="paragraph", text=text, confidence=1.0)]
    chunks = chunk_blocks(blocks, "txt", max_chars=400, overlap=0, enable_hierarchy=False)

    assert not any(c.metadata.parent_content for c in chunks)
