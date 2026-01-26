from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from rag.agent.executor import AgentExecutor
from rag.agent.planner import Planner
from rag.agent.tools import AgentTools
from rag.chunking.chunker import chunk_blocks
from rag.generation.llm_client import LLMClient, MockLLMClient
from rag.indexing.bm25_index import BM25Index
from rag.indexing.hybrid_retriever import HybridRetriever
from rag.indexing.vector_store import VectorStore
from rag.ingestion.loader import iter_documents
from rag.ingestion.parser import parse_document
from rag.validation.validator import validate_answer
from rag.config import get_settings
import uuid

DATA_DIR = Path("data")
UPLOAD_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "indices"
OUTPUT_DIR = Path("output")
ANSWERS_DIR = OUTPUT_DIR / "answers"
LOGS_DIR = OUTPUT_DIR / "logs"


class Pipeline:
    def __init__(self) -> None:
        self.settings = get_settings()
        for d in [UPLOAD_DIR, PROCESSED_DIR, INDEX_DIR, ANSWERS_DIR, LOGS_DIR]:
            d.mkdir(parents=True, exist_ok=True)
        self.bm25 = BM25Index(INDEX_DIR / "bm25")
        self.vector = VectorStore(
            persist_directory=str(INDEX_DIR / "vector"),
            embedding_model=self.settings.embedding_model,
        )
        self.hybrid = HybridRetriever(self.bm25, self.vector)
        self.tools = AgentTools(self.bm25, self.vector, self.hybrid)
        llm_key = self.settings.gemini_api_key
        self.llm = LLMClient(api_key=llm_key) if llm_key else MockLLMClient()
        self.planner = Planner(self.tools, self.llm)
        self.executor = AgentExecutor(self.planner, self.llm)
        self.cached_chunks: List[dict] = []

    def ingest_uploads(self) -> dict:
        # Reset cached view; BM25/vector are upserts so re-indexing is safe
        self.cached_chunks = []
        files = iter_documents(UPLOAD_DIR)
        total_chunks = 0
        indexed_files = 0
        errors: List[dict] = []

        for f in files:
            try:
                parsed = parse_document(f)
                doc_type = f.suffix.lower().lstrip(".") or "unknown"
                chunks = chunk_blocks(parsed.blocks, doc_type=doc_type)

                if chunks:
                    self.bm25.index_documents(chunks)
                    self.vector.index_documents(chunks)

                self.cached_chunks.extend(
                    [
                        {
                            "doc_id": c.metadata.doc_id,
                            "doc_type": c.metadata.doc_type,
                            "chunk_id": c.metadata.chunk_id,
                            "chunk_type": c.metadata.chunk_type,
                            "page": c.metadata.page,
                            "section": c.metadata.section,
                            "content": c.content,
                        }
                        for c in chunks
                    ]
                )
                total_chunks += len(chunks)
                indexed_files += 1
            except Exception as exc:
                errors.append({"file": str(f), "error": str(exc)})
                continue

        return {
            "files_detected": len(files),
            "files_indexed": indexed_files,
            "chunks_indexed": total_chunks,
            "errors": errors,
        }

    def query(self, question: str, filters: Optional[dict] = None) -> dict:
        exec_result = self.executor.run(question, filters)
        contexts = [r.get("content", "") for r in exec_result.results][:5]
        llm_payload = self.executor.llm.generate(contexts, question)
        validation = validate_answer(llm_payload)
        answer_path = None
        try:
            ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
            answer_id = uuid.uuid4().hex[:8]
            answer_path = ANSWERS_DIR / f"answer_{answer_id}.json"
            answer_path.write_text(json.dumps(llm_payload, indent=2))
            
            # Also save detailed logs
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            log_path = LOGS_DIR / f"log_{answer_id}.json"
            log_data = {
                "question": question,
                "filters": filters,
                "plan": [
                    {"tool": s.tool, "k": s.k, "note": s.note} 
                    for s in exec_result.plan.steps
                ],
                "intent": exec_result.plan.intent,
                "execution_log": exec_result.log,
                "validation": validation
            }
            log_path.write_text(json.dumps(log_data, indent=2))
        except Exception:
            answer_path = None
        
        return {
            "plan": exec_result.plan,
            "retrieval": exec_result.results,
            "llm": llm_payload,
            "validation": validation,
            "log": exec_result.log,
            "answer_path": str(answer_path) if answer_path else None,
        }

    def saved_chunks(self) -> List[dict]:
        return self.cached_chunks


def load_pipeline() -> Pipeline:
    return Pipeline()
