import json
from pathlib import Path

from rag.eval.audit_summary import build_audit_summary, write_audit_summary


def test_build_audit_summary_from_events(tmp_path: Path):
    events_path = tmp_path / "events.jsonl"
    rows = [
        {
            "timestamp_utc": "2026-02-07T00:00:00+00:00",
            "event_type": "query_finished",
            "durations_ms": {"total_ms": 100.0},
            "counts": {"retrieval_count": 4},
            "quality": {"validation_valid": True, "citation_hit": True},
        },
        {
            "timestamp_utc": "2026-02-07T00:00:01+00:00",
            "event_type": "query_finished",
            "durations_ms": {"total_ms": 500.0},
            "counts": {"retrieval_count": 2},
            "quality": {"validation_valid": False, "citation_hit": False},
        },
        {
            "timestamp_utc": "2026-02-07T00:00:02+00:00",
            "event_type": "ingestion_job_finished",
        },
    ]
    events_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    summary = build_audit_summary(events_path)
    assert summary["query_count"] == 2
    assert summary["ingestion_jobs_finished"] == 1
    assert summary["invalid_answer_rate"] == 0.5
    assert summary["citation_hit_rate"] == 0.5
    assert summary["p95_latency_ms"] >= 100.0


def test_write_audit_summary(tmp_path: Path):
    summary = {"query_count": 0}
    out = write_audit_summary(summary, tmp_path)
    assert out.exists()
