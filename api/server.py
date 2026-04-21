"""FastAPI backend wrapping the existing RAG Pipeline."""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so that `from src.rag...` works
# when running from any working directory.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from src.rag.config import get_settings  # noqa: E402
from src.rag.pipeline import ANSWERS_DIR, Pipeline  # noqa: E402
from src.rag.utils import database as db  # noqa: E402
from src.rag.visualization.graph_builder import build_chunk_graph  # noqa: E402
from src.rag.chunking.metadata import ChunkMetadata, DocumentChunk  # noqa: E402

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    question: str
    filters: dict[str, Any] | None = None
    mode: str = "default"


class QueryResponse(BaseModel):
    request_id: str
    rewritten_query: str | None = None
    llm: dict[str, Any] = Field(default_factory=dict)
    retrieval: list[dict[str, Any]] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)
    quality: dict[str, Any] = Field(default_factory=dict)
    feature_flags: dict[str, Any] = Field(default_factory=dict)
    timing_ms: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None


class UploadResponse(BaseModel):
    job_id: str | None = None
    status: str
    saved_files: list[str] = Field(default_factory=list)


class JobResponse(BaseModel):
    job_id: str
    status: str
    files_detected: int = 0
    processed_files: int = 0
    files_indexed: int = 0
    chunks_indexed: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
    timing_ms: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    error_code: str | None = None


class GraphNode(BaseModel):
    id: str
    node_type: str = ""
    doc_id: str = ""
    chunk_id: str = ""
    page: int = 0
    section: str = ""
    chunk_type: str = ""
    semantic_group_id: str = ""
    source_hash: str = ""
    content_preview: str = ""


class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: str = ""
    weight: float = 1.0
    reason: str = ""


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class AdminSettingsRequest(BaseModel):
    vector_enabled: bool | None = None
    reranker_enabled: bool | None = None
    hyde_enabled: bool | None = None
    deep_rewrite_enabled: bool | None = None
    decomposition_enabled: bool | None = None
    bm25_weight: float | None = None
    vector_weight: float | None = None


class ProviderInfo(BaseModel):
    parser: str
    embeddings: str
    llm: str


class AdminSettingsResponse(BaseModel):
    vector_enabled: bool
    vector_available: bool
    reranker_enabled: bool
    hyde_enabled: bool
    deep_rewrite_enabled: bool
    decomposition_enabled: bool
    bm25_weight: float
    vector_weight: float
    tuning: dict[str, Any]
    providers: ProviderInfo


class TuningRequest(BaseModel):
    ingestion_parse_workers: int | None = None
    ingestion_parse_queue_size: int | None = None
    embedding_batch_size: int | None = None
    vector_upsert_batch_size: int | None = None
    bm25_commit_batch_size: int | None = None
    chunking_mode: str | None = None
    index_swap_mode: str | None = None


class StatusResponse(BaseModel):
    status: str
    has_index: bool
    warmup: dict[str, Any] = Field(default_factory=dict)
    document_count: int = 0
    chunk_count: int = 0
    citation_rate: float = 0.0
    avg_latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Pipeline singleton via lifespan
# ---------------------------------------------------------------------------

_pipeline: Pipeline | None = None


def _get_pipeline() -> Pipeline:
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized yet.")
    return _pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pipeline
    _pipeline = Pipeline(lazy_init=True)
    try:
        import asyncio
        await asyncio.to_thread(_pipeline.warm_up)
    except Exception as exc:
        import logging
        logging.getLogger("api").warning("Pipeline warm-up failed (will retry on first request): %s", exc)
    yield
    _pipeline = None


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Multi-Model Agentic RAG API",
    version="1.0.0",
    description="REST API for the multi-model agentic RAG pipeline.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper: make Pipeline plan objects JSON-serialisable
# ---------------------------------------------------------------------------

def _serialise_plan(plan: Any) -> Any:
    """Convert plan objects to JSON-friendly dicts."""
    if plan is None:
        return None
    if isinstance(plan, (str, int, float, bool)):
        return plan
    if isinstance(plan, dict):
        return {k: _serialise_plan(v) for k, v in plan.items()}
    if isinstance(plan, (list, tuple)):
        return [_serialise_plan(item) for item in plan]
    # Dataclass / named-tuple / arbitrary object with __dict__
    if hasattr(plan, "__dict__"):
        return {k: _serialise_plan(v) for k, v in plan.__dict__.items()}
    return str(plan)


# ---------------------------------------------------------------------------
# GET /api/status
# ---------------------------------------------------------------------------

def _compute_query_stats() -> tuple[float, float]:
    """Compute citation rate and avg latency from SQLite."""
    try:
        return db.get_query_stats()
    except Exception:
        return 0.0, 0.0


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Pipeline health and warm-up status."""
    pipe = _get_pipeline()
    warmup_result = pipe.warm_up()
    chunks = pipe.saved_chunks()
    docs = pipe.list_documents()
    citation_rate, avg_latency = _compute_query_stats()
    return StatusResponse(
        status=warmup_result.get("status", "unknown"),
        has_index=pipe.has_ready_index(),
        warmup=warmup_result,
        document_count=len(docs),
        chunk_count=len(chunks),
        citation_rate=citation_rate,
        avg_latency_ms=avg_latency,
    )


# ---------------------------------------------------------------------------
# POST /api/query  — supports both plain JSON and SSE streaming
# ---------------------------------------------------------------------------

@app.post("/api/query")
async def post_query(body: QueryRequest):
    """
    Query the pipeline. Returns the full response as JSON.

    If the ``Accept`` header contains ``text/event-stream`` the response is
    delivered as a server-sent event stream with a single ``data`` frame
    carrying the JSON payload, followed by ``[DONE]``.
    """
    pipe = _get_pipeline()
    try:
        result = pipe.query_fast(
            question=body.question,
            filters=body.filters,
            mode=body.mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Serialise non-trivial objects (e.g. plan dataclass)
    serialised = _serialise_plan(result)

    async def _sse_generator():
        yield f"data: {json.dumps(serialised)}\n\n"
        yield "data: [DONE]\n\n"

    # Always return SSE so the contract is consistent for streaming clients.
    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# POST /api/upload
# ---------------------------------------------------------------------------

@app.post("/api/upload", response_model=UploadResponse)
async def upload_files(files: list[UploadFile] = File(...)):
    """
    Upload one or more files, save to temp, and kick off an ingestion job.
    """
    pipe = _get_pipeline()

    # Wrap UploadFile objects so that the Pipeline's save_uploaded_files can
    # work with them (it expects objects with .name + .read()/.getvalue()).
    class _UploadWrapper:
        def __init__(self, name: str, data: bytes):
            self.name = name
            self._data = data

        def getvalue(self) -> bytes:
            return self._data

        def read(self) -> bytes:
            return self._data

    wrappers = []
    for f in files:
        content = await f.read()
        wrappers.append(_UploadWrapper(f.filename or "upload", content))

    result = pipe.start_ingestion_job_for_uploads(wrappers)
    return UploadResponse(
        job_id=result.get("job_id"),
        status=result.get("status", "unknown"),
        saved_files=result.get("saved_files", []),
    )


# ---------------------------------------------------------------------------
# GET /api/jobs
# ---------------------------------------------------------------------------

@app.get("/api/jobs")
async def list_jobs():
    """List all ingestion jobs."""
    pipe = _get_pipeline()
    return pipe.list_ingestion_jobs()


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id}
# ---------------------------------------------------------------------------

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Single ingestion job status."""
    pipe = _get_pipeline()
    job = pipe.get_ingestion_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return job


# ---------------------------------------------------------------------------
# GET /api/chunks
# ---------------------------------------------------------------------------

@app.get("/api/chunks")
async def get_chunks():
    """All indexed chunks from the active catalog."""
    pipe = _get_pipeline()
    chunks = pipe.saved_chunks()
    return [{**c, "id": c.get("chunk_id")} for c in chunks]


# ---------------------------------------------------------------------------
# GET /api/documents
# ---------------------------------------------------------------------------

@app.get("/api/documents")
async def get_documents():
    """Document ID list."""
    pipe = _get_pipeline()
    return pipe.list_documents()


# ---------------------------------------------------------------------------
# DELETE /api/documents/{doc_id}
# ---------------------------------------------------------------------------

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and all its chunks from every index."""
    pipe = _get_pipeline()
    result = pipe.delete_document(doc_id)
    if not result.get("deleted"):
        raise HTTPException(status_code=404, detail=result.get("error", "Document not found"))
    return result


# ---------------------------------------------------------------------------
# GET /api/graph
# ---------------------------------------------------------------------------

@app.get("/api/graph", response_model=GraphResponse)
async def get_graph():
    """
    Build and return the knowledge graph as ``{nodes, edges}`` JSON.
    """
    pipe = _get_pipeline()
    chunks_raw = pipe.saved_chunks()

    # Reconstruct DocumentChunk objects from catalog dicts
    doc_chunks: list[DocumentChunk] = []
    for row in chunks_raw:
        meta = ChunkMetadata(
            doc_id=row.get("doc_id", ""),
            doc_type=row.get("doc_type", ""),
            page=int(row.get("page", 0)),
            section=row.get("section", ""),
            chunk_id=row.get("chunk_id", ""),
            chunk_type=row.get("chunk_type", "paragraph"),
            table_id=row.get("table_id"),
            confidence=float(row.get("confidence", 1.0)),
            source_path=row.get("source_path"),
            source_hash=row.get("source_hash"),
            ingest_timestamp_utc=row.get("ingest_timestamp_utc"),
            is_table=bool(row.get("is_table", False)),
            is_image=bool(row.get("is_image", False)),
            semantic_group_id=row.get("semantic_group_id"),
            boundary_reason=row.get("boundary_reason"),
        )
        doc_chunks.append(DocumentChunk(metadata=meta, content=row.get("content", "")))

    graph = build_chunk_graph(doc_chunks)

    nodes: list[GraphNode] = []
    for node_id, attrs in graph.nodes(data=True):
        nodes.append(
            GraphNode(
                id=str(node_id),
                node_type=attrs.get("node_type", ""),
                doc_id=attrs.get("doc_id", ""),
                chunk_id=attrs.get("chunk_id", ""),
                page=int(attrs.get("page", 0)),
                section=str(attrs.get("section", "")),
                chunk_type=str(attrs.get("chunk_type", "")),
                semantic_group_id=str(attrs.get("semantic_group_id", "")),
                source_hash=str(attrs.get("source_hash", "")),
                content_preview=str(attrs.get("content_preview", "")),
            )
        )

    edges: list[GraphEdge] = []
    for src, tgt, attrs in graph.edges(data=True):
        edges.append(
            GraphEdge(
                source=str(src),
                target=str(tgt),
                edge_type=str(attrs.get("edge_type", "")),
                weight=float(attrs.get("weight", 1.0)),
                reason=str(attrs.get("reason", "")),
            )
        )

    return GraphResponse(nodes=nodes, edges=edges)


# ---------------------------------------------------------------------------
# GET /api/answers
# ---------------------------------------------------------------------------

@app.get("/api/answers")
async def get_answers():
    """Return saved answers from SQLite."""
    try:
        rows = db.get_all_answers()
        if rows:
            return rows
    except Exception:
        pass
    # Fallback to file-based answers
    answers: list[dict[str, Any]] = []
    answers_dir = ANSWERS_DIR
    if not answers_dir.exists():
        return answers
    for path in sorted(answers_dir.glob("answer_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_filename"] = path.name
            answers.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return answers


# ---------------------------------------------------------------------------
# GET /api/admin/settings
# ---------------------------------------------------------------------------

def _build_provider_info(settings: Any) -> ProviderInfo:
    parser_status = "LlamaParse" if settings.llama_cloud_api_key else "not configured"
    embed_status = settings.embedding_model if settings.nvidia_api_key else "not configured"

    # Build LLM status from actually-configured providers
    chain = settings.llm_fallback_chain or ""
    models = [m.strip() for m in chain.split(",") if m.strip()]
    has_groq = bool(settings.groq_api_key)
    has_openrouter = bool(settings.openrouter_api_key)

    if not has_groq and not has_openrouter:
        llm_status = "not configured"
    else:
        # Filter to only models whose provider key is actually set
        available = []
        for m in models:
            provider = m.split(":")[0] if ":" in m else ""
            if provider == "groq" and has_groq:
                available.append(m)
            elif provider == "openrouter" and has_openrouter:
                available.append(m)
            elif provider not in ("groq", "openrouter"):
                available.append(m)

        if not available:
            providers_list = []
            if has_groq:
                providers_list.append("Groq")
            if has_openrouter:
                providers_list.append("OpenRouter")
            llm_status = " + ".join(providers_list) if providers_list else "not configured"
        else:
            primary = available[0]
            provider_name = primary.split(":")[0].capitalize() if ":" in primary else "LLM"
            model_name = primary.split(":")[-1] if ":" in primary else primary
            if len(available) > 1:
                llm_status = f"{provider_name} ({model_name}) +{len(available) - 1} fallback"
            else:
                llm_status = f"{provider_name} ({model_name})"

    return ProviderInfo(parser=parser_status, embeddings=embed_status, llm=llm_status)


@app.get("/api/admin/settings", response_model=AdminSettingsResponse)
async def get_admin_settings():
    """All feature flags, retriever weights, and ingestion tuning."""
    pipe = _get_pipeline()
    settings = get_settings()
    bm25_w, vector_w = pipe.get_retriever_weights()

    return AdminSettingsResponse(
        vector_enabled=bool(settings.vector_enabled),
        vector_available=pipe.is_vector_available(),
        reranker_enabled=bool(settings.reranker_enabled),
        hyde_enabled=bool(settings.hyde_enabled),
        deep_rewrite_enabled=bool(settings.deep_rewrite_enabled),
        decomposition_enabled=bool(settings.decomposition_enabled),
        bm25_weight=bm25_w,
        vector_weight=vector_w,
        tuning=pipe.get_ingestion_tuning(),
        providers=_build_provider_info(settings),
    )


# ---------------------------------------------------------------------------
# POST /api/admin/settings
# ---------------------------------------------------------------------------

@app.post("/api/admin/settings", response_model=AdminSettingsResponse)
async def update_admin_settings(body: AdminSettingsRequest):
    """Update feature toggles and/or retriever weights."""
    pipe = _get_pipeline()

    if body.vector_enabled is not None:
        pipe.set_vector_enabled(body.vector_enabled)
    if body.reranker_enabled is not None:
        pipe.set_reranker_enabled(body.reranker_enabled)
    if body.hyde_enabled is not None:
        pipe.set_hyde_enabled(body.hyde_enabled)
    if body.deep_rewrite_enabled is not None:
        pipe.set_deep_rewrite_enabled(body.deep_rewrite_enabled)
    if body.decomposition_enabled is not None:
        pipe.set_decomposition_enabled(body.decomposition_enabled)
    if body.bm25_weight is not None or body.vector_weight is not None:
        current_bm25, current_vector = pipe.get_retriever_weights()
        new_bm25 = body.bm25_weight if body.bm25_weight is not None else current_bm25
        new_vector = body.vector_weight if body.vector_weight is not None else current_vector
        pipe.update_retriever_weights(new_bm25, new_vector)

    settings = get_settings()
    bm25_w, vector_w = pipe.get_retriever_weights()

    return AdminSettingsResponse(
        vector_enabled=bool(settings.vector_enabled),
        vector_available=pipe.is_vector_available(),
        reranker_enabled=bool(settings.reranker_enabled),
        hyde_enabled=bool(settings.hyde_enabled),
        deep_rewrite_enabled=bool(settings.deep_rewrite_enabled),
        decomposition_enabled=bool(settings.decomposition_enabled),
        bm25_weight=bm25_w,
        vector_weight=vector_w,
        tuning=pipe.get_ingestion_tuning(),
        providers=_build_provider_info(settings),
    )


# ---------------------------------------------------------------------------
# GET /api/admin/index
# ---------------------------------------------------------------------------

@app.get("/api/admin/index")
async def get_index_status():
    """Index registry status."""
    pipe = _get_pipeline()
    return pipe.get_index_registry_status()


# ---------------------------------------------------------------------------
# POST /api/admin/index/switch
# ---------------------------------------------------------------------------

@app.post("/api/admin/index/switch")
async def switch_index():
    """Switch to the latest clean index."""
    pipe = _get_pipeline()
    result = pipe.switch_to_latest_clean_index()
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# POST /api/admin/tuning
# ---------------------------------------------------------------------------

@app.post("/api/admin/tuning")
async def update_tuning(body: TuningRequest):
    """Update ingestion tuning parameters."""
    pipe = _get_pipeline()
    current = pipe.get_ingestion_tuning()

    new_values = {
        "ingestion_parse_workers": (
            body.ingestion_parse_workers
            if body.ingestion_parse_workers is not None
            else current["ingestion_parse_workers"]
        ),
        "ingestion_parse_queue_size": (
            body.ingestion_parse_queue_size
            if body.ingestion_parse_queue_size is not None
            else current["ingestion_parse_queue_size"]
        ),
        "embedding_batch_size": (
            body.embedding_batch_size
            if body.embedding_batch_size is not None
            else current["embedding_batch_size"]
        ),
        "vector_upsert_batch_size": (
            body.vector_upsert_batch_size
            if body.vector_upsert_batch_size is not None
            else current["vector_upsert_batch_size"]
        ),
        "bm25_commit_batch_size": (
            body.bm25_commit_batch_size
            if body.bm25_commit_batch_size is not None
            else current["bm25_commit_batch_size"]
        ),
        "chunking_mode": (
            body.chunking_mode
            if body.chunking_mode is not None
            else current["chunking_mode"]
        ),
        "index_swap_mode": (
            body.index_swap_mode
            if body.index_swap_mode is not None
            else current["index_swap_mode"]
        ),
    }

    result = pipe.set_ingestion_tuning(**new_values)
    return result


# ---------------------------------------------------------------------------
# POST /api/admin/tuning/reset
# ---------------------------------------------------------------------------

@app.post("/api/admin/tuning/reset")
async def reset_tuning():
    """Reset ingestion tuning to defaults."""
    pipe = _get_pipeline()
    return pipe.reset_ingestion_tuning_defaults()


# ---------------------------------------------------------------------------
# Entrypoint for `python -m api.server` or `uvicorn api.server:app`
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
