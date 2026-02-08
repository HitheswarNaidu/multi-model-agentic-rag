from pathlib import Path

from rag.config import get_settings
from rag.ingestion.parser import Block, DocumentParseResult
from rag.pipeline import Pipeline


def test_parse_chunk_parallel_preserves_file_order(tmp_path: Path, monkeypatch):
    files = [tmp_path / "b.pdf", tmp_path / "a.pdf"]
    for file_path in files:
        file_path.write_text("x", encoding="utf-8")

    def fake_parse(path, settings=None):
        return DocumentParseResult(
            blocks=[
                Block(
                    doc_id=path.name,
                    page=1,
                    chunk_type="paragraph",
                    text=f"content:{path.name}",
                    confidence=1.0,
                )
            ]
        )

    monkeypatch.setattr("rag.pipeline.parse_document", fake_parse)

    p = Pipeline()
    summary = p.parse_chunk_parallel(
        job_id="job_test",
        files=files,
        chunk_size=100,
        chunk_overlap=0,
        enable_hierarchy=False,
        chunking_mode="window",
    )

    ordered_names = [Path(item["file"]).name for item in summary["parsed_outputs"]]
    assert ordered_names == ["b.pdf", "a.pdf"]
    assert summary["timing_ms"]["parse_total"] >= 0.0
    assert summary["timing_ms"]["chunk_total"] >= 0.0


def test_ingest_files_reports_stage_timing(tmp_path: Path, monkeypatch):
    import rag.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(pipeline_mod, "UPLOAD_DIR", tmp_path / "data" / "uploads")
    monkeypatch.setattr(pipeline_mod, "PROCESSED_DIR", tmp_path / "data" / "processed")
    monkeypatch.setattr(pipeline_mod, "INDEX_DIR", tmp_path / "data" / "indices")
    monkeypatch.setattr(pipeline_mod, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(pipeline_mod, "ANSWERS_DIR", tmp_path / "output" / "answers")
    monkeypatch.setattr(pipeline_mod, "LOGS_DIR", tmp_path / "output" / "logs")

    uploads = tmp_path / "data" / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    file_path = uploads / "test.pdf"
    file_path.write_text("content", encoding="utf-8")

    def fake_parse(path, settings=None):
        return DocumentParseResult(
            blocks=[
                Block(
                    doc_id=path.name,
                    page=1,
                    chunk_type="paragraph",
                    text="hello world",
                    confidence=1.0,
                )
            ]
        )

    monkeypatch.setattr("rag.pipeline.parse_document", fake_parse)
    monkeypatch.setenv("DOCLING_OCR_FORCE", "false")

    p = Pipeline()
    summary = p.ingest_uploads(files=[file_path])

    assert "timing_ms" in summary
    assert "parse_total" in summary["timing_ms"]
    assert "bm25_write_total" in summary["timing_ms"]
    assert "vector_upsert_total" in summary["timing_ms"]
    assert "swap_total" in summary["timing_ms"]
    assert "throughput" in summary
    assert summary["chunks_indexed"] >= 1


def test_start_ingestion_job_fails_fast_when_ocr_config_invalid(tmp_path: Path, monkeypatch):
    import rag.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(pipeline_mod, "UPLOAD_DIR", tmp_path / "data" / "uploads")
    monkeypatch.setattr(pipeline_mod, "PROCESSED_DIR", tmp_path / "data" / "processed")
    monkeypatch.setattr(pipeline_mod, "INDEX_DIR", tmp_path / "data" / "indices")
    monkeypatch.setattr(pipeline_mod, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(pipeline_mod, "ANSWERS_DIR", tmp_path / "output" / "answers")
    monkeypatch.setattr(pipeline_mod, "LOGS_DIR", tmp_path / "output" / "logs")
    monkeypatch.setenv("DOCLING_OCR_FORCE", "true")
    monkeypatch.delenv("DOCLING_OCR_DET_MODEL_PATH", raising=False)
    monkeypatch.delenv("DOCLING_OCR_CLS_MODEL_PATH", raising=False)
    monkeypatch.delenv("DOCLING_OCR_REC_MODEL_PATH", raising=False)
    monkeypatch.delenv("DOCLING_OCR_REC_KEYS_PATH", raising=False)
    monkeypatch.delenv("DOCLING_OCR_FONT_PATH", raising=False)
    get_settings.cache_clear()

    uploads = tmp_path / "data" / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    file_path = uploads / "needs-ocr.pdf"
    file_path.write_text("content", encoding="utf-8")

    p = Pipeline()
    job_id = p.start_ingestion_job(files=[file_path])
    status = p.get_ingestion_job(job_id)

    assert status is not None
    assert status["status"] == "failed"
    assert status["error_code"] == "OCR_CONFIG_INVALID"
    assert "DOCLING_OCR_DET_MODEL_PATH" in status.get("missing_fields", [])
    get_settings.cache_clear()
