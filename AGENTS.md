# AGENTS

Repository rules for agent-assisted implementation and review.

## Product Direction

- Chat-first multipage UX is the default information architecture:
  - `Chat`, `Data Store`, `Knowledge Graph`, `Admin`
- UI upload and auto-queued indexing are required.
- Strict Docling OCR mode is optional (`DOCLING_OCR_FORCE=false` default).
- Vector retrieval is optional (`VECTOR_ENABLED=false` default, BM25-only supported).

## Core Principles

- Keep fast path (`mode=default`) low-latency and predictable.
- Keep deep features optional and explicitly toggleable.
- No unauditable behavior: query/ingestion flows must emit structured events.

## Mandatory Verification Before Completion

```bash
ruff check src app tests
pytest -q
python src/batch_runner.py data/sample_questions.json --eval --mode default --max-invalid-rate 0.20 --max-p95-latency-ms 2500 --min-citation-hit-rate 0.80
```

## Coding Standards

- No dead code, duplicate logic, or bare `except:`.
- Preserve compatibility wrapper: `Pipeline.query(...)`.
- Preserve query audit fields: `request_id`, `timing_ms`, `quality`, `latency_ms` alias.
- Emit explicit `error.code` in failure paths.

## Observability Contract

Write runtime events to:

- `output/logs/events.jsonl`

Required IDs:

- query: `request_id`
- ingestion: `job_id`

OCR validation events are mandatory:

- `ocr_config_validated`
- `ocr_config_error`

## Documentation Expectation

When behavior changes, update:

- `README.md`
- `CHANGELOG.md`
- `GEMINI.md`
- `CLAUDE.md`
- `docs/specs.md`
- `docs/agent.md`
- `docs/edge_cases.md`
- `docs/quickstart.md`
- `docs/progress.md`
- `docs/deployment.md`

## Preferred Work Pattern

1. Add/adjust tests.
2. Implement minimal behavior changes.
3. Remove duplication/dead code.
4. Run full verification gates.
5. Update docs/changelog.
