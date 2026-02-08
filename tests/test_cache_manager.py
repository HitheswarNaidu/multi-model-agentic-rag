from rag.utils.cache_manager import CacheManager


def test_cache_manager_clears_dirs(tmp_path):
    data_dir = tmp_path / "data"
    indices = data_dir / "indices"
    uploads = data_dir / "uploads"

    indices.mkdir(parents=True)
    uploads.mkdir(parents=True)

    (indices / "dummy_index.txt").write_text("index data")
    (uploads / "dummy_file.txt").write_text("file data")

    cm = CacheManager(data_dir)
    cm.clear_all()

    assert indices.exists()
    assert uploads.exists()
    assert not (indices / "dummy_index.txt").exists()
    assert not (uploads / "dummy_file.txt").exists()
