from pathlib import Path

from rag.pipeline import Pipeline


def test_pipeline_ingest_and_query(tmp_path: Path, monkeypatch):
    # Arrange: create a temp uploads directory with a tiny PDF
    uploads = tmp_path / "data" / "uploads"
    uploads.mkdir(parents=True)
    pdf_path = uploads / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF")

    # Redirect pipeline data dirs by monkeypatching module constants
    import rag.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(pipeline_mod, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(pipeline_mod, "PROCESSED_DIR", tmp_path / "data" / "processed")
    monkeypatch.setattr(pipeline_mod, "INDEX_DIR", tmp_path / "data" / "indices")
    monkeypatch.setattr(pipeline_mod, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(pipeline_mod, "ANSWERS_DIR", tmp_path / "output" / "answers")
    monkeypatch.setattr(pipeline_mod, "LOGS_DIR", tmp_path / "output" / "logs")

    # Use lightweight embedding model to avoid large downloads during tests
    monkeypatch.setenv("EMBEDDING_MODEL", "hash-embedding")

    p = Pipeline()
    # Act
    summary = p.ingest_uploads()
    resp = p.query("What is this document about?")

    # Assert
    assert isinstance(summary, dict)
    assert summary.get("files_detected", 0) >= 1
    assert summary.get("chunks_indexed", 0) >= 0
    assert "llm" in resp
    assert "validation" in resp
