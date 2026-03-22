# ruff: noqa: E402

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rag.config import get_settings


@pytest.fixture
def temp_docs(tmp_path: Path) -> Path:
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    yield uploads
    shutil.rmtree(uploads, ignore_errors=True)


@pytest.fixture(autouse=True)
def default_test_settings(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "hash-embedding")
    monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("NVIDIA_API_KEY", "")
    monkeypatch.setenv("VECTOR_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
