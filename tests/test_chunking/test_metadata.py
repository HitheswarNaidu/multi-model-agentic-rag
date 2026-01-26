from rag.chunking.metadata import ChunkMetadata, DocumentChunk


def test_metadata_fields():
    meta = ChunkMetadata(
        doc_id="doc1",
        doc_type="pdf",
        page=1,
        section="intro",
        chunk_id="c1",
        chunk_type="paragraph",
        table_id=None,
        confidence=0.9,
    )
    chunk = DocumentChunk(metadata=meta, content="hello")
    assert chunk.metadata.doc_id == "doc1"
    assert chunk.metadata.chunk_type == "paragraph"
    assert chunk.content == "hello"
