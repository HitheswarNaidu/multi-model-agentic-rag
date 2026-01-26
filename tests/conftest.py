import shutil
import sys
from pathlib import Path

import pytest


# Ensure src/ is on path for tests
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def temp_docs(tmp_path: Path) -> Path:
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    yield uploads
    shutil.rmtree(uploads, ignore_errors=True)
