from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round(0.95 * (len(ordered) - 1)))
    return ordered[idx]


def _lower_list(values: list[str]) -> list[str]:
    return [str(v).lower() for v in values]


def run_eval(pipeline, questions: list[dict[str, Any]], mode: str = "default") -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    latencies: list[float] = []
    recall_scores: list[float] = []
    citation_hits: list[bool] = []
    answer_hits: list[bool] = []
    invalid_count = 0

    for item in questions:
        question = item.get("question", "")
        filters = item.get("filters")
        expected_chunks = item.get("expected_chunks") or []
        expected_answer_contains = _lower_list(item.get("expected_answer_contains") or [])

        t0 = perf_counter()
        try:
            resp = pipeline.query_fast(question, filters=filters, mode=mode)
            query_error = None
        except Exception as exc:
            resp = {
                "retrieval": [],
                "llm": {"answer": "", "provenance": []},
                "validation": {"valid": False, "issues": ["query_exception"]},
                "latency_ms": {"total_ms": (perf_counter() - t0) * 1000.0},
            }
            query_error = {
                "code": "EVAL_QUERY_FAILED",
                "message": str(exc),
            }
        retrieval = resp.get("retrieval", []) or []
        retrieval_ids = [r.get("chunk_id") for r in retrieval if r.get("chunk_id")]
        llm = resp.get("llm", {}) or {}
        answer_text = str(llm.get("answer", ""))
        provenance = llm.get("provenance", []) or []
        validation = resp.get("validation", {}) or {}
        valid = bool(validation.get("valid", False))
        latency = float((resp.get("latency_ms", {}) or {}).get("total_ms", 0.0))

        if not valid:
            invalid_count += 1
        latencies.append(latency)

        recall = None
        if expected_chunks:
            matched = len(set(expected_chunks) & set(retrieval_ids))
            recall = matched / max(1, len(expected_chunks))
            recall_scores.append(recall)

        citation_hit = None
        if provenance:
            citation_hit = all(cid in retrieval_ids for cid in provenance)
            citation_hits.append(citation_hit)

        answer_hit = None
        if expected_answer_contains:
            answer_lower = answer_text.lower()
            answer_hit = all(term in answer_lower for term in expected_answer_contains)
            answer_hits.append(answer_hit)

        runs.append(
            {
                "id": item.get("id"),
                "question": question,
                "mode": mode,
                "retrieval_count": len(retrieval_ids),
                "retrieval_ids": retrieval_ids,
                "provenance": provenance,
                "validation": validation,
                "latency_ms": latency,
                "recall_at_k": recall,
                "citation_hit": citation_hit,
                "answer_contains_hit": answer_hit,
                "answer_preview": answer_text[:240],
                "error": query_error,
            }
        )

    total = len(runs) or 1
    metrics = {
        "total_questions": len(runs),
        "retrieval_recall_at_k": round(mean(recall_scores), 4) if recall_scores else None,
        "citation_hit_rate": round(sum(1 for x in citation_hits if x) / len(citation_hits), 4)
        if citation_hits
        else None,
        "answer_contains_rate": round(sum(1 for x in answer_hits if x) / len(answer_hits), 4)
        if answer_hits
        else None,
        "invalid_answer_rate": round(invalid_count / total, 4),
        "p95_latency_ms": round(_p95(latencies), 2),
        "avg_latency_ms": round(mean(latencies), 2) if latencies else 0.0,
    }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "metrics": metrics,
        "runs": runs,
    }


def save_eval_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"eval_{ts}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path
