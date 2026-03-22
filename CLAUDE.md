# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

```bash
# Run Streamlit app
python -m streamlit run app/main.py

# Run tests
pytest -q

# Run a single test file
pytest tests/test_agent/test_planner.py -q

# Lint
ruff check src app tests

# Eval gates (batch runner with SLA thresholds)
python src/batch_runner.py data/sample_questions.json --eval --mode default \
  --max-invalid-rate 0.20 --max-p95-latency-ms 2500 --min-citation-hit-rate 0.80

# Verify environment setup
python verify_setup.py
```

## Architecture

**Multipage Streamlit app** (`app/`) with four pages:
- **Chat** (`pages/1_💬_Chat.py`) — primary UX: file upload, auto-queued indexing, query, answers with citations.
- **Data Store** (`pages/2_🗄️_Data_Store.py`) — chunk browser, saved answers archive.
- **Knowledge Graph** (`pages/3_🕸️_Knowledge_Graph.py`) — interactive graph investigation (not just static viz). Keep controls minimal.
- **Admin** (`pages/4_🛠️_Admin.py`) — feature toggles, retrieval weights, provider status, index diagnostics.

**Core pipeline** (`src/rag/`):

```
Query → IntentClassifier → Planner → AgentExecutor
         ↓                    ↓            ↓
   (intent type)     (PlanStep list)   retrieval → LLM (Groq/OpenRouter) → Validator
```

- `pipeline.py` — top-level orchestrator: ingestion, query, index management, startup integrity checks.
- `config.py` — Pydantic `Settings` from env vars (`.env`). Cached via `lru_cache`; tests must call `get_settings.cache_clear()`.
- `agent/` — planner, executor, intent classifier, tools (bm25_search, vector_search, hybrid_search, table_row_search). Advanced helpers (query_expander, decomposer, hyde_generator, query_rewriter) are ON by default.
- `ingestion/` — parser (LlamaParse cloud API), loader (file discovery).
- `chunking/` — window mode (default) and semantic-hybrid mode with boundary detection.
- `indexing/` — BM25 (Whoosh), vector store (Chroma + NVIDIA embeddings, ON by default), hybrid retriever (RRF fusion), reranker (ON by default).
- `generation/` — LLM client with configurable fallback chain (Groq primary, OpenRouter fallback), prompt templates, answer refiner.
- `validation/` — citation presence and groundedness checks.
- `utils/` — audit_logger (events.jsonl), index_registry (version tracking), job_store (ingestion status), cache_manager, date_extractor.
- `eval/` — harness for batch evaluation with SLA gates.

**Data layout:**
```
data/indices/versions/{index_id}/   # bm25/, vector/, chunk_catalog.jsonl
data/indices/index_registry.json    # active index pointer
data/uploads/                       # user files
```

## Key Design Decisions

- **Vector+BM25 hybrid by default.** `VECTOR_ENABLED=true`. NVIDIA embeddings (`nvidia/llama-nemotron-embed-1b-v2`) via API.
- **All advanced RAG features ON by default:** HyDE, query rewrite, decomposition, reranker are all enabled in `mode=default`.
- **LlamaParse cloud parsing.** Document parsing via `LLAMA_CLOUD_API_KEY`; no local OCR dependencies.
- **Configurable LLM fallback chain.** `LLM_FALLBACK_CHAIN` env var (default: Groq primary, OpenRouter fallback).
- **Index integrity at startup.** Pipeline detects demo/test markers and auto-switches to latest clean index.
- **Structured audit events** to `output/logs/events.jsonl` with `request_id` (query) / `job_id` (ingestion). Index integrity and LLM provider tracking events are required.
- **Quota failures are explicit:** surface `LLM_QUOTA_EXHAUSTED`, never ambiguous fallback.

## Test Conventions

- `tests/conftest.py` sets `EMBEDDING_MODEL=hash-embedding` (deterministic, no GPU) as autouse defaults.
- Tests are organized by module: `test_ingestion/`, `test_chunking/`, `test_indexing/`, `test_agent/`, `test_generation/`, `test_validation/`, `test_visualization/`, `test_eval/`.
- E2E tests: `test_e2e.py`, `test_full_architecture.py`, `test_pipeline_fast_path.py`.
- Performance tests: `test_startup_speed.py`, `test_kg_performance_guardrails.py`.

## Coding Standards

- Line length 100 (ruff + black). Python 3.10+.
- No dead code, no bare `except:`.
- Preserve `Pipeline.query(...)` compatibility wrapper.
- Preserve audit fields: `request_id`, `timing_ms`, `quality`, `latency_ms`.
- Emit explicit `error.code` in failure paths.

## Documentation Updates

When behavior changes, update: `README.md`, `CHANGELOG.md`, `AGENTS.md`, `CLAUDE.md`, and relevant files under `docs/` (specs, agent, edge_cases, quickstart, progress, deployment).
