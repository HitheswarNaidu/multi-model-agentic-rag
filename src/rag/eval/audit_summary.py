from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round(0.95 * (len(ordered) - 1)))
    return ordered[idx]


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError:
                continue
    return rows


def build_audit_summary(events_path: Path) -> dict:
    events = _read_jsonl(events_path)
    query_finished = [e for e in events if e.get("event_type") == "query_finished"]
    ingestion_finished = [e for e in events if e.get("event_type") == "ingestion_job_finished"]
    errors = [e for e in events if e.get("event_type") == "error"]

    total_latencies = [
        float((e.get("durations_ms", {}) or {}).get("total_ms", 0.0)) for e in query_finished
    ]
    invalid_count = sum(
        1
        for e in query_finished
        if not bool((e.get("quality", {}) or {}).get("validation_valid", False))
    )
    citation_values = [
        (e.get("quality", {}) or {}).get("citation_hit")
        for e in query_finished
        if (e.get("quality", {}) or {}).get("citation_hit") is not None
    ]
    retrieval_counts = [
        int((e.get("counts", {}) or {}).get("retrieval_count", 0))
        for e in query_finished
    ]

    total_queries = len(query_finished)
    invalid_rate = (invalid_count / total_queries) if total_queries else 0.0
    citation_hit_rate = (
        sum(1 for v in citation_values if v) / len(citation_values)
        if citation_values
        else None
    )

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_events_file": str(events_path),
        "query_count": total_queries,
        "ingestion_jobs_finished": len(ingestion_finished),
        "error_count": len(errors),
        "p95_latency_ms": round(_p95(total_latencies), 2) if total_latencies else 0.0,
        "avg_latency_ms": round(mean(total_latencies), 2) if total_latencies else 0.0,
        "invalid_answer_rate": round(invalid_rate, 4),
        "citation_hit_rate": round(citation_hit_rate, 4) if citation_hit_rate is not None else None,
        "avg_retrieval_count": round(mean(retrieval_counts), 2) if retrieval_counts else 0.0,
    }


def write_audit_summary(summary: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = output_dir / f"audit_summary_{stamp}.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return out_path
