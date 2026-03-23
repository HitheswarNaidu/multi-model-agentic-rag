# AGENTS

Repository rules for agent-assisted implementation and review.

## Product Direction

- Two-tier architecture: Next.js frontend (`frontend/`) + FastAPI backend (`api/server.py`).
- Four pages: Chat, Data Store, Knowledge Graph, Admin.
- Graphite dark theme (burnt orange accent, no light mode).
- LlamaParse cloud parsing via `LLAMA_CLOUD_API_KEY`.
- Vector retrieval ON by default (NVIDIA embeddings via `NVIDIA_API_KEY`).
- All advanced RAG features ON by default.
- LLM fallback chain: Groq primary, OpenRouter fallback.

## Core Principles

- No unauditable behavior: query/ingestion flows must emit structured events with LLM provider tracking.
- Pipeline (`src/rag/`) must remain decoupled from frontend — only `api/server.py` bridges them.
- Frontend calls backend via REST/SSE only — no direct Python imports from Next.js.

## Mandatory Verification Before Completion

```bash
ruff check src api tests
pytest -q
cd frontend && npm run build
python src/batch_runner.py data/sample_questions.json --eval --mode default \
  --max-invalid-rate 0.20 --max-p95-latency-ms 2500 --min-citation-hit-rate 0.80
```

## Coding Standards

- Python: line length 100 (ruff). Python 3.10+.
- TypeScript: Next.js 14 App Router conventions. shadcn/ui v4 components.
- No dead code, duplicate logic, or bare `except:`.
- Preserve `Pipeline.query(...)` compatibility wrapper.
- Preserve query audit fields: `request_id`, `timing_ms`, `quality`, `latency_ms`.
- Emit explicit `error.code` in failure paths.

## Observability Contract

Runtime events: `output/logs/events.jsonl`

Required IDs:
- query: `request_id`
- ingestion: `job_id`

LLM provider tracking:
- `_llm_provider`, `_llm_model`, `_llm_fallback_used`

## Documentation Expectation

When behavior changes, update: `README.md`, `CHANGELOG.md`, `AGENTS.md`, `CLAUDE.md`.

## Preferred Work Pattern

1. Add/adjust tests.
2. Implement minimal behavior changes.
3. Remove duplication/dead code.
4. Run full verification gates.
5. Update docs/changelog.
