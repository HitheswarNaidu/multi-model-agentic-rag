from pathlib import Path

from rag.utils.index_registry import IndexRegistry


def test_index_registry_create_and_activate(tmp_path: Path):
    index_root = tmp_path / "indices"
    registry = IndexRegistry(index_root / "index_registry.json", index_root)

    initial = registry.ensure_initialized()
    assert initial["active"]["index_id"] == "legacy"

    staging = registry.create_staging("job123")
    assert staging["index_id"] == "index_job123"
    assert registry.get_staging() is not None

    activation = registry.activate_staging("job123")
    assert activation["active"]["index_id"] == "index_job123"
    assert registry.get_staging() is None


def test_index_registry_set_active(tmp_path: Path):
    index_root = tmp_path / "indices"
    registry = IndexRegistry(index_root / "index_registry.json", index_root)
    registry.ensure_initialized()

    payload = {
        "index_id": "index_clean",
        "bm25_dir": str((index_root / "versions" / "index_clean" / "bm25").resolve()),
        "vector_dir": str((index_root / "versions" / "index_clean" / "vector").resolve()),
        "chunk_catalog": str(
            (index_root / "versions" / "index_clean" / "chunk_catalog.jsonl").resolve()
        ),
    }
    result = registry.set_active(payload)
    assert result["active"]["index_id"] == "index_clean"
    assert registry.get_active()["index_id"] == "index_clean"
