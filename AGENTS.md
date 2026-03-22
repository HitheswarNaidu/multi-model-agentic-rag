# AGENTS

Repository rules for agent-assisted implementation and review.

## Product Direction

- Chat-first multipage UX is the default information architecture:
  - `Chat`, `Data Store`, `Knowledge Graph`, `Admin`
- UI upload and auto-queued indexing are required.
- LlamaParse cloud parsing via `LLAMA_CLOUD_API_KEY`.
- Vector retrieval is ON by default (NVIDIA embeddings via `NVIDIA_API_KEY`).

## Core Principles

- All advanced RAG features (HyDE, query rewrite, decomposition, reranker) are ON by default.
- LLM provider chain is configurable via `LLM_FALLBACK_CHAIN` (Groq primary, OpenRouter fallback).
- No unauditable behavior: query/ingestion flows must emit structured events with LLM provider tracking.

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

LLM provider tracking events are required:

- `_llm_provider`
- `_llm_model`
- `_llm_fallback_used`

## Documentation Expectation

When behavior changes, update:

- `README.md`
- `CHANGELOG.md`
- `AGENTS.md`
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
