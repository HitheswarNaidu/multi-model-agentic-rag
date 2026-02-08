import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def clear_indices(self):
        index_dir = self.data_dir / "indices"
        if index_dir.exists():
            shutil.rmtree(index_dir)
            logger.info(f"Cleared indices at {index_dir}")
            index_dir.mkdir()

    def clear_uploads(self):
        upload_dir = self.data_dir / "uploads"
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
            logger.info(f"Cleared uploads at {upload_dir}")
            upload_dir.mkdir()

    def clear_all(self):
        self.clear_indices()
        self.clear_uploads()
        # Also clear processed if exists
        processed = self.data_dir / "processed"
        if processed.exists():
            shutil.rmtree(processed)
            processed.mkdir()
