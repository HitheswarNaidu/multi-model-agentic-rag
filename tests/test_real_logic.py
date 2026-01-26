import shutil
from pathlib import Path
from rag.chunking.chunker import chunk_blocks
from rag.ingestion.parser import Block
from rag.indexing.bm25_index import BM25Index
from rag.chunking.metadata import DocumentChunk, ChunkMetadata

def test_table_row_chunking():
    table_text = "Row 1 Col 1\tRow 1 Col 2\nRow 2 Col 1\tRow 2 Col 2"
    block = Block(
        doc_id="doc1",
        page=1,
        chunk_type="table",
        text=table_text,
        confidence=0.9,
        table_id="table1"
    )
    
    chunks = chunk_blocks([block], doc_type="pdf")
    
    # Should produce 2 chunks
    assert len(chunks) == 2
    assert chunks[0].metadata.chunk_type == "row"
    assert chunks[0].content == "Row 1 Col 1\tRow 1 Col 2"
    assert chunks[1].metadata.chunk_type == "row"
    assert chunks[1].metadata.table_id == "table1"

def test_bm25_filtering(tmp_path):
    idx_dir = tmp_path / "bm25_test"
    bm25 = BM25Index(idx_dir)
    
    c1 = DocumentChunk(
        metadata=ChunkMetadata(
            doc_id="doc1", doc_type="pdf", page=1, section="A", 
            chunk_id="c1", chunk_type="paragraph", table_id=None, confidence=1.0
        ),
        content="apple banana"
    )
    c2 = DocumentChunk(
        metadata=ChunkMetadata(
            doc_id="doc2", doc_type="docx", page=1, section="B", 
            chunk_id="c2", chunk_type="paragraph", table_id=None, confidence=1.0
        ),
        content="apple orange"
    )
    
    bm25.index_documents([c1, c2])
    
    # Search for apple, filter by doc_type=docx
    results = bm25.search("apple", doc_type="docx")
    
    assert len(results) == 1
    assert results[0]["doc_id"] == "doc2"

def test_clarification_intent_and_prompt():
    from rag.agent.intent_classifier import classify_intent
    from rag.generation.prompts import build_prompt
    
    # Test intent
    vague_query = "data"
    assert classify_intent(vague_query) == "clarification"
    
    # Test prompt
    prompt = build_prompt(["ctx"], vague_query, intent="clarification")
    assert "suggest a clarification question" in prompt

