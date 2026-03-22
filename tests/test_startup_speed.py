from types import SimpleNamespace

import verify_setup
from rag.pipeline import Pipeline


def test_verify_setup_quick_uses_find_spec(monkeypatch):
    calls: list[str] = []

    def fake_find_spec(name: str):
        calls.append(name)
        return SimpleNamespace()

    monkeypatch.setattr(verify_setup.importlib.util, "find_spec", fake_find_spec)
    assert verify_setup.check_packages_quick() is True
    assert len(calls) == len(verify_setup.REQUIRED_PACKAGES)


def test_verify_setup_full_uses_import_module(monkeypatch):
    calls: list[str] = []

    def fake_import_module(name: str):
        calls.append(name)
        return SimpleNamespace()

    monkeypatch.setattr(verify_setup.importlib, "import_module", fake_import_module)
    assert verify_setup.check_packages_full() is True
    assert len(calls) == len(verify_setup.REQUIRED_PACKAGES)


def test_pipeline_lazy_init_and_warmup(tmp_path, monkeypatch):
    import rag.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(pipeline_mod, "UPLOAD_DIR", tmp_path / "data" / "uploads")
    monkeypatch.setattr(pipeline_mod, "PROCESSED_DIR", tmp_path / "data" / "processed")
    monkeypatch.setattr(pipeline_mod, "INDEX_DIR", tmp_path / "data" / "indices")
    monkeypatch.setattr(pipeline_mod, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(pipeline_mod, "ANSWERS_DIR", tmp_path / "output" / "answers")
    monkeypatch.setattr(pipeline_mod, "LOGS_DIR", tmp_path / "output" / "logs")
    monkeypatch.setenv("EMBEDDING_MODEL", "hash-embedding")

    p = Pipeline(lazy_init=True)
    assert p._runtime_ready is False

    result = p.warm_up()
    assert result["status"] in {"ready", "failed"}
    assert "duration_ms" in result

    events_path = tmp_path / "output" / "logs" / "events.jsonl"
    if events_path.exists():
        text = events_path.read_text(encoding="utf-8")
        assert "warmup_started" in text
