import json
import time
from pathlib import Path

from rag.config import get_settings
from rag.pipeline import Pipeline


def _build_pipeline(tmp_path: Path, monkeypatch) -> Pipeline:
    import rag.pipeline as pipeline_mod

    uploads = tmp_path / "data" / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(pipeline_mod, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(pipeline_mod, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(pipeline_mod, "PROCESSED_DIR", tmp_path / "data" / "processed")
    monkeypatch.setattr(pipeline_mod, "INDEX_DIR", tmp_path / "data" / "indices")
    monkeypatch.setattr(pipeline_mod, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(pipeline_mod, "ANSWERS_DIR", tmp_path / "output" / "answers")
    monkeypatch.setattr(pipeline_mod, "LOGS_DIR", tmp_path / "output" / "logs")

    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("EMBEDDING_MODEL", "hash-embedding")
    monkeypatch.setenv("VECTOR_ENABLED", "false")
    monkeypatch.setenv("FAST_PATH_ENABLED", "true")

    return Pipeline()


def test_vector_conflict_falls_back_to_bm25_only(tmp_path, monkeypatch):
    import rag.pipeline as pipeline_mod

    uploads = tmp_path / "data" / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(pipeline_mod, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(pipeline_mod, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(pipeline_mod, "PROCESSED_DIR", tmp_path / "data" / "processed")
    monkeypatch.setattr(pipeline_mod, "INDEX_DIR", tmp_path / "data" / "indices")
    monkeypatch.setattr(pipeline_mod, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(pipeline_mod, "ANSWERS_DIR", tmp_path / "output" / "answers")
    monkeypatch.setattr(pipeline_mod, "LOGS_DIR", tmp_path / "output" / "logs")

    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("EMBEDDING_MODEL", "all-mpnet-base-v2")
    monkeypatch.setenv("VECTOR_ENABLED", "true")
    get_settings.cache_clear()

    def _raise_conflict(*args, **kwargs):
        raise ValueError(
            "An embedding function already exists in the collection configuration. "
            "Embedding function conflict: new: sentence-transformer vs persisted: hash-embedding"
        )

    monkeypatch.setattr(pipeline_mod, "VectorStore", _raise_conflict)

    p = Pipeline()
    p.set_reranker_enabled(False)

    assert not p.is_vector_available()
    bm25_weight, vector_weight = p.get_retriever_weights()
    assert bm25_weight == 1.0
    assert vector_weight == 0.0
    get_settings.cache_clear()


def test_query_fast_returns_audit_fields(tmp_path, monkeypatch):
    p = _build_pipeline(tmp_path, monkeypatch)

    response = p.query_fast("hello")

    assert "request_id" in response
    assert "timing_ms" in response
    assert "quality" in response
    assert "rewrite_ms" in response["timing_ms"]
    assert "plan_ms" in response["timing_ms"]
    assert "validation_ms" in response["timing_ms"]
    assert "validation_valid" in response["quality"]

    assert "latency_ms" in response
    assert "retrieval_ms" in response["latency_ms"]
    assert "llm_ms" in response["latency_ms"]
    assert "total_ms" in response["latency_ms"]


def test_query_wrapper_respects_fast_path_flag(tmp_path, monkeypatch):
    p = _build_pipeline(tmp_path, monkeypatch)

    called = {}

    def _fake_query_fast(question, filters=None, mode="default"):
        called["mode"] = mode
        return {"llm": {"answer": "ok", "provenance": []}, "validation": {"valid": True}}

    monkeypatch.setattr(p, "query_fast", _fake_query_fast)

    p.settings.fast_path_enabled = True
    p.query("test")
    assert called["mode"] == "default"

    p.settings.fast_path_enabled = False
    p.query("test")
    assert called["mode"] == "deep"


def test_start_ingestion_job_and_read_status(tmp_path, monkeypatch):
    p = _build_pipeline(tmp_path, monkeypatch)

    job_id = p.start_ingestion_job()
    assert job_id

    status = p.get_ingestion_job(job_id)
    assert status is not None
    assert status["status"] in {"queued", "running", "completed", "failed"}

    # Wait briefly for background ingestion to finish.
    deadline = time.time() + 60
    while time.time() < deadline:
        status = p.get_ingestion_job(job_id)
        if status and status["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)

    assert status["status"] in {"completed", "failed"}
    assert "error_code" in status


def test_query_fast_writes_structured_events(tmp_path, monkeypatch):
    p = _build_pipeline(tmp_path, monkeypatch)
    response = p.query_fast("hello")
    request_id = response["request_id"]

    events_file = tmp_path / "output" / "logs" / "events.jsonl"
    assert events_file.exists()

    events = []
    for line in events_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))

    event_types = {e.get("event_type") for e in events if e.get("request_id") == request_id}
    assert "query_started" in event_types
    assert "query_finished" in event_types


def test_query_fast_llm_failure_falls_back_and_logs_error(tmp_path, monkeypatch):
    p = _build_pipeline(tmp_path, monkeypatch)
    p.warm_up()

    def _boom(*args, **kwargs):
        raise RuntimeError("quota exceeded")

    monkeypatch.setattr(p.llm, "generate", _boom)

    response = p.query_fast("hello")
    assert response["error"]["code"] == "LLM_GENERATION_FAILED"
    assert response["llm"]["answer"].startswith("INSUFFICIENT_DATA")

    events_file = tmp_path / "output" / "logs" / "events.jsonl"
    events = [
        json.loads(line)
        for line in events_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    request_id = response["request_id"]
    request_events = [e for e in events if e.get("request_id") == request_id]
    assert any(e.get("event_type") == "error" for e in request_events)


def test_query_fast_quota_failure_maps_to_explicit_code(tmp_path, monkeypatch):
    p = _build_pipeline(tmp_path, monkeypatch)
    p.warm_up()

    def _boom(*args, **kwargs):
        raise RuntimeError("429 RESOURCE_EXHAUSTED quota exceeded")

    monkeypatch.setattr(p.llm, "generate", _boom)

    response = p.query_fast("hello")
    assert response["error"]["code"] == "LLM_QUOTA_EXHAUSTED"
    assert response["llm"]["error"]["code"] == "LLM_QUOTA_EXHAUSTED"
    assert "quota" in response["llm"]["answer"].lower()


def test_startup_auto_switches_from_demo_index(tmp_path, monkeypatch):
    import rag.pipeline as pipeline_mod

    p = _build_pipeline(tmp_path, monkeypatch)
    versions = pipeline_mod.INDEX_DIR / "versions"

    demo_root = versions / "index_sync_demo"
    clean_root = versions / "index_clean_real"
    (demo_root / "bm25").mkdir(parents=True, exist_ok=True)
    (demo_root / "vector").mkdir(parents=True, exist_ok=True)
    (clean_root / "bm25").mkdir(parents=True, exist_ok=True)
    (clean_root / "vector").mkdir(parents=True, exist_ok=True)

    (demo_root / "chunk_catalog.jsonl").write_text(
        json.dumps(
            {
                "doc_id": "doc1",
                "chunk_id": "doc1-1-0-P0-C0",
                "content": "Apple revenue is $100.",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (clean_root / "chunk_catalog.jsonl").write_text(
        json.dumps(
            {
                "doc_id": "Certificate.pdf",
                "chunk_id": "Certificate.pdf-1-0-P0-C0",
                "content": "Real certificate content",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    p.index_registry.set_active(
        {
            "index_id": "index_sync_demo",
            "bm25_dir": str((demo_root / "bm25").resolve()),
            "vector_dir": str((demo_root / "vector").resolve()),
            "chunk_catalog": str((demo_root / "chunk_catalog.jsonl").resolve()),
        }
    )
    p.settings.ignore_test_demo_indexes = True
    p.warm_up()

    status = p.get_index_registry_status()
    assert status["active"]["index_id"] == "index_clean_real"
    assert bool(status["integrity"]["suspicious"]) is False
