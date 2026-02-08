from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    """Append-only JSONL job log with latest-state lookup by job_id."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def create_job(self, payload: dict) -> str:
        job_id = payload.get("job_id") or uuid4().hex[:12]
        event = {
            "job_id": job_id,
            "created_at": payload.get("created_at") or _utc_now_iso(),
            "updated_at": payload.get("updated_at") or _utc_now_iso(),
            **payload,
        }
        event["job_id"] = job_id
        self._append(event)
        return job_id

    def update_job(self, job_id: str, patch: dict) -> dict:
        base = self.get_job(job_id) or {"job_id": job_id, "created_at": _utc_now_iso()}
        updated = {**base, **patch, "job_id": job_id, "updated_at": _utc_now_iso()}
        self._append(updated)
        return updated

    def get_job(self, job_id: str) -> dict | None:
        latest: dict | None = None
        for row in self._read_rows():
            if row.get("job_id") == job_id:
                latest = row
        return latest

    def list_jobs(self) -> list[dict]:
        by_id: dict[str, dict] = {}
        for row in self._read_rows():
            jid = row.get("job_id")
            if jid:
                by_id[jid] = row
        return sorted(
            by_id.values(),
            key=lambda x: x.get("updated_at", x.get("created_at", "")),
            reverse=True,
        )

    def has_completed_job(self) -> bool:
        for row in self.list_jobs():
            if row.get("status") == "completed":
                return True
        return False

    def _append(self, data: dict) -> None:
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=True) + "\n")

    def _read_rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        out: list[dict] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                try:
                    out.append(json.loads(s))
                except json.JSONDecodeError:
                    continue
        return out

