from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_request_id() -> str:
    return uuid4().hex[:12]


def hash_query(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()


class AuditLogger:
    def __init__(self, events_path: Path) -> None:
        self.events_path = Path(events_path)
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def log_event(self, event_type: str, **payload) -> dict:
        event = {
            "timestamp_utc": utc_now_iso(),
            "event_type": event_type,
            **payload,
        }
        self._append_jsonl(event)
        return event

    def _append_jsonl(self, event: dict) -> None:
        with self._lock:
            with self.events_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=True) + "\n")
