import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from rag.eval.audit_summary import build_audit_summary, write_audit_summary
from rag.eval.harness import run_eval, save_eval_report
from rag.ingestion.loader import iter_documents
from rag.pipeline import load_pipeline

DEFAULT_MAX_INVALID_RATE = 0.20
DEFAULT_MAX_P95_LATENCY_MS = 2500.0
DEFAULT_MIN_CITATION_HIT_RATE = 0.80


def run_batch(input_file: Path, output_file: Path, mode: str = "default"):
    print("Loading pipeline...")
    pipeline = load_pipeline()

    print(f"Reading questions from {input_file}...")
    questions = json.loads(input_file.read_text(encoding="utf-8"))

    results = []
    for idx, item in enumerate(questions):
        q = item.get("question")
        filters = item.get("filters")
        print(f"[{idx + 1}/{len(questions)}] Processing: {q}")

        resp = pipeline.query_fast(q, filters=filters, mode=mode)

        results.append(
            {
                "id": item.get("id"),
                "question": q,
                "answer": resp["llm"].get("answer"),
                "provenance": resp["llm"].get("provenance"),
                "validation_valid": resp["validation"].get("valid"),
                "validation_issues": resp["validation"].get("issues"),
                "latency_ms": resp.get("latency_ms", {}),
            }
        )

    print(f"Writing results to {output_file}...")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("Done.")


def run_eval_mode(
    input_file: Path,
    mode: str = "default",
    output_dir: Path = Path("output/eval"),
    max_invalid_rate: float = DEFAULT_MAX_INVALID_RATE,
    max_p95_latency_ms: float = DEFAULT_MAX_P95_LATENCY_MS,
    min_citation_hit_rate: float = DEFAULT_MIN_CITATION_HIT_RATE,
) -> int:
    print("Loading pipeline...")
    pipeline = load_pipeline()
    print(f"Loading eval questions from {input_file}...")
    questions = json.loads(input_file.read_text(encoding="utf-8"))
    report = run_eval(pipeline, questions, mode=mode)
    report_path = save_eval_report(report, output_dir=output_dir)
    print(f"Saved eval report to {report_path}")
    metrics = report["metrics"]
    print(json.dumps(metrics, indent=2))
    audit_summary = build_audit_summary(Path("output/logs/events.jsonl"))
    summary_path = write_audit_summary(audit_summary, Path("output/logs"))
    print(f"Saved audit summary to {summary_path}")

    failures = []
    if metrics.get("invalid_answer_rate") is not None:
        if metrics["invalid_answer_rate"] > max_invalid_rate:
            failures.append(
                f"invalid_answer_rate={metrics['invalid_answer_rate']} > {max_invalid_rate}"
            )
    if metrics.get("p95_latency_ms") is not None:
        if metrics["p95_latency_ms"] > max_p95_latency_ms:
            failures.append(f"p95_latency_ms={metrics['p95_latency_ms']} > {max_p95_latency_ms}")
    if metrics.get("citation_hit_rate") is not None:
        if metrics["citation_hit_rate"] < min_citation_hit_rate:
            failures.append(
                f"citation_hit_rate={metrics['citation_hit_rate']} < {min_citation_hit_rate}"
            )

    if failures:
        print("EVAL GATE FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 2
    return 0


def run_ingestion_benchmark(
    input_dir: Path,
    repeats: int,
    chunk_size: int,
    chunk_overlap: int,
    enable_hierarchy: bool,
    output_dir: Path,
    baseline_file: Path | None,
    max_regression_pct: float | None,
) -> int:
    print("Loading pipeline...")
    pipeline = load_pipeline()
    files = iter_documents(input_dir)
    print(f"Benchmark files: {len(files)} from {input_dir}")
    if not files:
        print("No benchmark files found. Exiting benchmark mode.")
        return 1

    runs: list[dict] = []
    for run_idx in range(1, repeats + 1):
        t0 = perf_counter()
        summary = pipeline.ingest_uploads(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            enable_hierarchy=enable_hierarchy,
            files=files,
        )
        duration_ms = (perf_counter() - t0) * 1000
        chunks = int(summary.get("chunks_indexed", 0))
        chunks_per_sec = round(chunks / max(duration_ms / 1000, 0.001), 2)
        runs.append(
            {
                "run": run_idx,
                "duration_ms": round(duration_ms, 2),
                "chunks_indexed": chunks,
                "chunks_per_sec": chunks_per_sec,
                "timing_ms": summary.get("timing_ms", {}),
                "throughput": summary.get("throughput", {}),
            }
        )
        print(f"[run {run_idx}] duration_ms={duration_ms:.2f} chunks={chunks} cps={chunks_per_sec}")

    avg_chunks_per_sec = round(sum(r["chunks_per_sec"] for r in runs) / len(runs), 2)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(input_dir),
        "repeats": repeats,
        "avg_chunks_per_sec": avg_chunks_per_sec,
        "runs": runs,
    }
    report_path = output_dir / f"ingestion_benchmark_{stamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved ingestion benchmark to {report_path}")

    if baseline_file and baseline_file.exists() and max_regression_pct is not None:
        baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
        baseline_cps = float(baseline.get("avg_chunks_per_sec", 0.0) or 0.0)
        if baseline_cps > 0:
            drop_pct = ((baseline_cps - avg_chunks_per_sec) / baseline_cps) * 100.0
            if drop_pct > max_regression_pct:
                print(
                    f"BENCHMARK GATE FAILED: throughput regression {drop_pct:.2f}% "
                    f"(baseline={baseline_cps}, current={avg_chunks_per_sec})"
                )
                return 2
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run batch queries or eval against the RAG pipeline.",
    )
    parser.add_argument("input", type=Path, nargs="?", help="JSON file with question objects")
    parser.add_argument("--output", type=Path, default=Path("output/batch_results.json"))
    parser.add_argument("--mode", choices=["default", "deep"], default="default")
    parser.add_argument("--eval", action="store_true", help="Run evaluation metrics mode")
    parser.add_argument("--eval-output-dir", type=Path, default=Path("output/eval"))
    parser.add_argument("--max-invalid-rate", type=float, default=DEFAULT_MAX_INVALID_RATE)
    parser.add_argument(
        "--max-p95-latency-ms",
        type=float,
        default=DEFAULT_MAX_P95_LATENCY_MS,
    )
    parser.add_argument(
        "--min-citation-hit-rate",
        type=float,
        default=DEFAULT_MIN_CITATION_HIT_RATE,
    )
    parser.add_argument(
        "--benchmark-ingestion",
        action="store_true",
        help="Run ingestion-only benchmark and write report.",
    )
    parser.add_argument(
        "--benchmark-input-dir",
        type=Path,
        default=Path("data/uploads"),
        help="Input directory for ingestion benchmark mode.",
    )
    parser.add_argument("--benchmark-repeats", type=int, default=1)
    parser.add_argument("--benchmark-chunk-size", type=int, default=800)
    parser.add_argument("--benchmark-chunk-overlap", type=int, default=80)
    parser.add_argument("--benchmark-disable-hierarchy", action="store_true")
    parser.add_argument(
        "--benchmark-output-dir",
        type=Path,
        default=Path("output/logs"),
    )
    parser.add_argument(
        "--benchmark-baseline-file",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--max-ingestion-regression-pct",
        type=float,
        default=None,
    )
    args = parser.parse_args()

    if args.benchmark_ingestion:
        raise SystemExit(
            run_ingestion_benchmark(
                input_dir=args.benchmark_input_dir,
                repeats=max(1, args.benchmark_repeats),
                chunk_size=max(100, args.benchmark_chunk_size),
                chunk_overlap=max(0, args.benchmark_chunk_overlap),
                enable_hierarchy=not args.benchmark_disable_hierarchy,
                output_dir=args.benchmark_output_dir,
                baseline_file=args.benchmark_baseline_file,
                max_regression_pct=args.max_ingestion_regression_pct,
            )
        )
    elif args.eval:
        if args.input is None:
            raise SystemExit("input is required for --eval mode")
        raise SystemExit(
            run_eval_mode(
                args.input,
                mode=args.mode,
                output_dir=args.eval_output_dir,
                max_invalid_rate=args.max_invalid_rate,
                max_p95_latency_ms=args.max_p95_latency_ms,
                min_citation_hit_rate=args.min_citation_hit_rate,
            )
        )
    else:
        if args.input is None:
            raise SystemExit("input is required for batch mode")
        run_batch(args.input, args.output, mode=args.mode)
