from pathlib import Path

from rag.agent.executor import AgentExecutor
from rag.agent.planner import Planner
from rag.agent.tools import AgentTools
from rag.chunking.metadata import ChunkMetadata, DocumentChunk
from rag.generation.llm_client import MockLLMClient
from rag.indexing.bm25_index import BM25Index
from rag.indexing.hybrid_retriever import HybridRetriever
from rag.indexing.vector_store import NoOpVectorStore


def _make_chunk(doc_id: str, idx: int, text: str) -> DocumentChunk:
    meta = ChunkMetadata(
        doc_id=doc_id,
        doc_type="pdf",
        page=1,
        section="",
        chunk_id=f"{doc_id}-1-0-P0-C{idx}",
        chunk_type="paragraph",
        table_id=None,
        confidence=1.0,
    )
    return DocumentChunk(metadata=meta, content=text)


def _make_executor(tmp_path: Path, llm_payload: dict) -> AgentExecutor:
    bm25 = BM25Index(tmp_path / "bm25")
    doc_id = "doc_summary.pdf"
    bm25.index_documents([
        _make_chunk(doc_id, 0, "This document is about retrieval augmented generation."),
        _make_chunk(doc_id, 1, "It includes indexing, chunking, and provenance citations."),
    ])
    vector = NoOpVectorStore()
    hybrid = HybridRetriever(bm25=bm25, vector=vector)
    tools = AgentTools(bm25=bm25, vector=vector, hybrid=hybrid)
    llm = MockLLMClient(payload=llm_payload)
    planner = Planner(tools, llm)
    return AgentExecutor(planner, llm)


def test_summarize_with_provenance_is_valid(tmp_path: Path):
    payload = {
        "answer": "Summary text",
        "provenance": ["doc_summary.pdf-1-0-P0-C0", "doc_summary.pdf-1-0-P0-C1"],
        "conflict": False,
    }
    executor = _make_executor(tmp_path, payload)
    result = executor.run(
        query="Summarize",
        filters={"doc_id": "doc_summary.pdf"},
        mode="deep",
    )
    assert result.validation["valid"] is True


def test_summarize_missing_provenance_returns_explicit_error(tmp_path: Path):
    payload = {
        "answer": "Summary without citations",
        "provenance": [],
        "conflict": False,
    }
    executor = _make_executor(tmp_path, payload)
    result = executor.run(
        query="Summarize",
        filters={"doc_id": "doc_summary.pdf"},
        mode="deep",
    )
    assert result.error is not None
    assert result.error["code"] == "SUMMARY_PROVENANCE_MISSING"
    assert result.validation["valid"] is False
