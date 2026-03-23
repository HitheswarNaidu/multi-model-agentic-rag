# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

```bash
# Start FastAPI backend
python -m uvicorn api.server:app --reload --port 8000

# Start Next.js frontend
cd frontend && npm run dev

# Run tests
pytest -q

# Run a single test file
pytest tests/test_agent/test_planner.py -q

# Lint
ruff check src api tests

# Eval gates (batch runner with SLA thresholds)
python src/batch_runner.py data/sample_questions.json --eval --mode default \
  --max-invalid-rate 0.20 --max-p95-latency-ms 2500 --min-citation-hit-rate 0.80

# Verify environment setup
python verify_setup.py
```

## Architecture

**Two-tier app**: Next.js frontend (`frontend/`) + FastAPI backend (`api/server.py`) wrapping the Python RAG pipeline (`src/rag/`).

**Frontend** (`frontend/`): Next.js 14 App Router, shadcn/ui v4, Tailwind CSS v4. Graphite dark theme (near-black `#1A1A1A` + burnt orange `#E8590C`). Four routes:
- `/chat` — file upload, Q&A with citations, Fast/Deep mode toggle.
- `/data-store` — TanStack Table chunk browser, saved answers.
- `/knowledge-graph` — canvas force-directed graph, node inspector.
- `/admin` — feature toggles, retrieval weights, provider status, index diagnostics.

**Backend API** (`api/server.py`): FastAPI app with 16 REST endpoints wrapping `Pipeline`. SSE streaming for `/api/query`. CORS enabled for `localhost:3000`.

**Core pipeline** (`src/rag/`):

```
Query -> IntentClassifier -> Planner -> AgentExecutor
          |                    |            |
    (intent type)     (PlanStep list)   retrieval -> LLM (Groq/OpenRouter) -> Validator
```

- `pipeline.py` — orchestrator: ingestion, query, index management, startup integrity checks.
- `config.py` — Pydantic `Settings` from env vars (`.env`). Cached via `lru_cache`; tests must call `get_settings.cache_clear()`.
- `agent/` — planner, executor, intent classifier, tools (bm25_search, vector_search, hybrid_search, table_row_search). Advanced helpers (query_expander, decomposer, hyde_generator, query_rewriter) ON by default.
- `ingestion/` — LlamaParse cloud parser, file loader.
- `chunking/` — window mode (default) and semantic-hybrid mode with boundary detection.
- `indexing/` — BM25 (Whoosh), vector (Chroma + NVIDIA embeddings), hybrid retriever (RRF fusion), reranker (cross-encoder).
- `generation/` — LLM client with Groq/OpenRouter fallback chain, prompt templates, answer refiner.
- `validation/` — citation presence and groundedness checks.
- `visualization/` — graph builder, interactive subgraph, node detail extraction.
- `utils/` — audit_logger, index_registry, job_store, cache_manager, date_extractor.
- `eval/` — batch evaluation harness with SLA gates.

**Data layout:**
```
data/indices/versions/{index_id}/   # bm25/, vector/, chunk_catalog.jsonl
data/indices/index_registry.json    # active index pointer
data/uploads/                       # user files
```

## Key Design Decisions

- **Vector+BM25 hybrid by default.** `VECTOR_ENABLED=true`. NVIDIA embeddings (`nvidia/llama-nemotron-embed-1b-v2`) via API.
- **All advanced RAG features ON by default:** HyDE, query rewrite, decomposition, reranker.
- **LlamaParse cloud parsing.** Document parsing via `LLAMA_CLOUD_API_KEY`; no local OCR dependencies.
- **Configurable LLM fallback chain.** `LLM_FALLBACK_CHAIN` env var (Groq primary, OpenRouter fallback).
- **Index integrity at startup.** Pipeline detects demo/test markers and auto-switches to latest clean index.
- **Structured audit events** to `output/logs/events.jsonl` with `request_id` / `job_id`.
- **Quota failures are explicit:** surface `LLM_QUOTA_EXHAUSTED`, never ambiguous fallback.
- **Frontend is dark-only Graphite theme.** No light mode toggle. Burnt orange accent throughout.

## Test Conventions

- `tests/conftest.py` sets `EMBEDDING_MODEL=hash-embedding` (deterministic, no GPU) as autouse defaults.
- Tests organized by module: `test_ingestion/`, `test_chunking/`, `test_indexing/`, `test_agent/`, `test_generation/`, `test_validation/`, `test_visualization/`, `test_eval/`.
- E2E tests: `test_e2e.py`, `test_full_architecture.py`, `test_pipeline_fast_path.py`.
- Performance tests: `test_startup_speed.py`, `test_kg_performance_guardrails.py`.
- `test_graph_state_bridge.py` is skipped (Streamlit legacy).

## Coding Standards

- Line length 100 (ruff). Python 3.10+.
- No dead code, no bare `except:`.
- Preserve `Pipeline.query(...)` compatibility wrapper.
- Preserve audit fields: `request_id`, `timing_ms`, `quality`, `latency_ms`.
- Emit explicit `error.code` in failure paths.

## Documentation Updates

When behavior changes, update: `README.md`, `CHANGELOG.md`, `AGENTS.md`, `CLAUDE.md`.
