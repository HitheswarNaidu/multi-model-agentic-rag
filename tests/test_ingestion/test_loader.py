from pathlib import Path

import pytest

from rag.ingestion.loader import SUPPORTED_EXTS, iter_documents, load_batch, validate_file


def test_validate_file_supports_known_types(tmp_path: Path):
    for ext in SUPPORTED_EXTS:
        f = tmp_path / f"sample{ext}"
        f.write_bytes(b"test")
        assert validate_file(f) == f.resolve()


def test_validate_file_rejects_unknown(tmp_path: Path):
    f = tmp_path / "sample.txt"
    f.write_bytes(b"test")
    with pytest.raises(ValueError):
        validate_file(f)


def test_iter_documents_finds_supported_files(tmp_path: Path):
    (tmp_path / "a.pdf").write_bytes(b"a")
    (tmp_path / "b.docx").write_bytes(b"b")
    (tmp_path / "ignore.txt").write_bytes(b"x")
    found = iter_documents(tmp_path)
    names = {p.name for p in found}
    assert names == {"a.pdf", "b.docx"}


def test_load_batch_validates_all(tmp_path: Path):
    f1 = tmp_path / "a.pdf"
    f2 = tmp_path / "b.docx"
    f1.write_bytes(b"a")
    f2.write_bytes(b"b")
    result = load_batch([f1, f2])
    assert result == [f1.resolve(), f2.resolve()]


def test_load_batch_raises_on_invalid(tmp_path: Path):
    f1 = tmp_path / "a.pdf"
    f1.write_bytes(b"a")
    with pytest.raises(ValueError):
        load_batch([f1, tmp_path / "bad.txt"])
