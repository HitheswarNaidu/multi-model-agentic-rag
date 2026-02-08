from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IndexRegistry:
    def __init__(self, registry_path: Path, index_root: Path):
        self.registry_path = Path(registry_path)
        self.index_root = Path(index_root)
        self.index_root.mkdir(parents=True, exist_ok=True)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def ensure_initialized(self) -> dict:
        if self.registry_path.exists():
            data = self._read()
            if data.get("active"):
                return data

        legacy_active = {
            "index_id": "legacy",
            "bm25_dir": str((self.index_root / "bm25").resolve()),
            "vector_dir": str((self.index_root / "vector").resolve()),
            "chunk_catalog": str((self.index_root / "chunk_catalog.jsonl").resolve()),
        }
        data = {
            "active": legacy_active,
            "staging": None,
            "updated_at": _utc_now_iso(),
        }
        self._write(data)
        return data

    def get_active(self) -> dict:
        data = self.ensure_initialized()
        active = data.get("active") or {}
        return {
            "index_id": str(active.get("index_id", "legacy")),
            "bm25_dir": str(active.get("bm25_dir", (self.index_root / "bm25").resolve())),
            "vector_dir": str(active.get("vector_dir", (self.index_root / "vector").resolve())),
            "chunk_catalog": str(
                active.get("chunk_catalog", (self.index_root / "chunk_catalog.jsonl").resolve())
            ),
        }

    def create_staging(self, job_id: str) -> dict:
        versions_dir = self.index_root / "versions"
        stage_root = versions_dir / f"index_{job_id}"
        stage_bm25 = stage_root / "bm25"
        stage_vector = stage_root / "vector"
        stage_catalog = stage_root / "chunk_catalog.jsonl"

        stage_bm25.mkdir(parents=True, exist_ok=True)
        stage_vector.mkdir(parents=True, exist_ok=True)
        stage_catalog.parent.mkdir(parents=True, exist_ok=True)

        staging = {
            "index_id": f"index_{job_id}",
            "job_id": job_id,
            "bm25_dir": str(stage_bm25.resolve()),
            "vector_dir": str(stage_vector.resolve()),
            "chunk_catalog": str(stage_catalog.resolve()),
            "created_at": _utc_now_iso(),
        }
        data = self.ensure_initialized()
        data["staging"] = staging
        data["updated_at"] = _utc_now_iso()
        self._write(data)
        return staging

    def activate_staging(self, job_id: str) -> dict:
        data = self.ensure_initialized()
        staging = data.get("staging")
        if not isinstance(staging, dict):
            raise ValueError("No staging index present")
        if staging.get("job_id") != job_id:
            raise ValueError("Staging index job mismatch")

        previous_active = data.get("active")
        data["active"] = {
            "index_id": staging["index_id"],
            "bm25_dir": staging["bm25_dir"],
            "vector_dir": staging["vector_dir"],
            "chunk_catalog": staging["chunk_catalog"],
        }
        data["staging"] = None
        data["updated_at"] = _utc_now_iso()
        self._write(data)
        return {
            "active": data["active"],
            "previous_active": previous_active,
        }

    def clear_staging(self) -> None:
        data = self.ensure_initialized()
        data["staging"] = None
        data["updated_at"] = _utc_now_iso()
        self._write(data)

    def set_active(self, active: dict) -> dict:
        required = {"index_id", "bm25_dir", "vector_dir", "chunk_catalog"}
        missing = [key for key in required if not str(active.get(key, "")).strip()]
        if missing:
            raise ValueError(f"Invalid active index payload: missing {', '.join(sorted(missing))}")
        data = self.ensure_initialized()
        previous_active = data.get("active")
        data["active"] = {
            "index_id": str(active["index_id"]),
            "bm25_dir": str(active["bm25_dir"]),
            "vector_dir": str(active["vector_dir"]),
            "chunk_catalog": str(active["chunk_catalog"]),
        }
        data["updated_at"] = _utc_now_iso()
        self._write(data)
        return {
            "active": data["active"],
            "previous_active": previous_active,
        }

    def get_staging(self) -> dict | None:
        data = self.ensure_initialized()
        staging = data.get("staging")
        return dict(staging) if isinstance(staging, dict) else None

    def _read(self) -> dict:
        try:
            return json.loads(self.registry_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write(self, data: dict) -> None:
        self.registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
