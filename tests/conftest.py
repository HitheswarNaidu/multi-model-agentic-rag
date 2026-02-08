# ruff: noqa: E402

import shutil
import sys
from pathlib import Path

import pytest

# Ensure src/ is on path for tests
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
    # Keep parser behavior lightweight for most tests unless a test overrides it.
    monkeypatch.setenv("DOCLING_OCR_FORCE", "false")
    monkeypatch.setenv("EMBEDDING_MODEL", "hash-embedding")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
