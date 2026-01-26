import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from rag.ingestion.parser import Block, DocumentParseResult
from rag.chunking.chunker import chunk_blocks
from rag.indexing.bm25_index import BM25Index
from rag.indexing.vector_store import VectorStore
from rag.indexing.hybrid_retriever import HybridRetriever
from rag.agent.tools import AgentTools
from rag.agent.planner import Planner, Plan
from rag.agent.executor import AgentExecutor
from rag.generation.llm_client import MockLLMClient
from rag.pipeline import Pipeline

def test_full_flow_mocked(tmp_path):
    # 1. Ingestion & Chunking
    blocks = [
        Block(doc_id="doc1", page=1, chunk_type="paragraph", text="Apple revenue is $100.", confidence=1.0),
        Block(doc_id="doc1", page=1, chunk_type="table", text="Item\tCost\nApple\t$1", confidence=0.9, table_id="t1")
    ]
    
    chunks = chunk_blocks(blocks, doc_type="pdf")
    
    # Check table splitting logic
    row_chunks = [c for c in chunks if c.metadata.chunk_type == "row"]
    assert len(row_chunks) >= 1
    assert "Apple\t$1" in row_chunks[0].content

    # 2. Indexing (Mocking IO)
    bm25_dir = tmp_path / "bm25"
    bm25 = BM25Index(bm25_dir)
    bm25.index_documents(chunks)
    
    # Verify BM25 search with filters
    res = bm25.search("Apple", chunk_type="row")
    assert len(res) > 0
    assert res[0]["metadata"]["chunk_type"] == "row"

    # 3. Vector Store (Mocking Chroma)
    with patch("chromadb.PersistentClient") as mock_client:
        # Mock collection behavior
        mock_coll = MagicMock()
        mock_coll.query.return_value = {
            "ids": [["c1"]],
            "documents": [["Apple cost is $1"]],
            "metadatas": [[{"doc_id": "doc1", "chunk_type": "row"}]],
            "distances": [[0.1]]
        }
        mock_client.return_value.get_or_create_collection.return_value = mock_coll
        
        vector = VectorStore(persist_directory=str(tmp_path / "vector"))
        
        # Test vector search call
        vector.search("cost", chunk_type="row")
        # Check if filter was passed to chroma
        call_args = mock_coll.query.call_args[1]
        assert call_args["where"]["chunk_type"] == "row"

    # 4. Agent & Planner
    # Re-instantiate objects to use the real BM25 and mocked Vector
    # (Simplified for this test, usually we'd pass the objects)
    
    # 5. Pipeline Logic check
    # We can check the pipeline's ingest method specifically for exception handling
    with patch("rag.pipeline.parse_document") as mock_parse:
        mock_parse.return_value = DocumentParseResult(blocks=blocks)
        
        p = Pipeline()
        # Mock the internal components to avoid heavy lifting
        p.bm25 = MagicMock()
        p.vector = MagicMock()
        
        # Test ingest
        summary = p.ingest_uploads() # Will look at UPLOAD_DIR
        # Since UPLOAD_DIR is empty in this env, files_detected should be 0, but no crash
        assert isinstance(summary, dict)

def test_executor_with_clarification():
    # Test the clarification flow
    planner = MagicMock()
    planner.make_plan.return_value = Plan(intent="clarification", steps=[])
    planner.execute.return_value = []
    
    llm = MagicMock()
    llm.generate.return_value = {"answer": "Clarification?", "provenance": []}
    
    executor = AgentExecutor(planner, llm)
    res = executor.run("what?")
    
    # Ensure intent was passed to generate
    llm.generate.assert_called_with([], "what?", intent="clarification")
