# Multimodal Agentic RAG

Local, feature-rich Agentic RAG with a FastAPI backend and Next.js frontend.

## Quick Start

```bash
# 1. Install Python deps
pip install -r requirements.txt

# 2. Install frontend deps
cd frontend && npm install && cd ..

# 3. Copy env and add your API keys
cp .env.example .env

# 4. Start both servers
run_app.bat
```

Or start manually:

```bash
# Terminal 1 — FastAPI backend (port 8000)
python -m uvicorn api.server:app --reload --port 8000

# Terminal 2 — Next.js frontend (port 3000)
cd frontend && npm run dev
```

Open http://localhost:3000

## Required API Keys

Set in `.env`:

```env
LLAMA_CLOUD_API_KEY=...       # LlamaParse document parsing
NVIDIA_API_KEY=...            # NVIDIA embedding API
GROQ_API_KEY=...              # Groq LLM (primary)
OPENROUTER_API_KEY=...        # OpenRouter LLM (fallback)
```

## Architecture

```
Next.js Frontend (port 3000)        FastAPI Backend (port 8000)
  /chat                               POST /api/query (SSE)
  /data-store                         POST /api/upload
  /knowledge-graph                    GET  /api/chunks, /api/graph
  /admin                              GET/POST /api/admin/settings
        |                                    |
        +------------- HTTP/SSE ------------+
                                             |
                                    Python RAG Pipeline (src/rag/)
```

**Frontend** (`frontend/`): Next.js 14 App Router + shadcn/ui v4 + Tailwind CSS. Graphite dark theme.

**Backend API** (`api/server.py`): FastAPI wrapping the Pipeline class. 16 REST endpoints.

**Core Pipeline** (`src/rag/`):

```
Query -> IntentClassifier -> Planner -> AgentExecutor
          |                    |            |
    (intent type)     (PlanStep list)   retrieval -> LLM (Groq/OpenRouter) -> Validator
```

- `pipeline.py` -- orchestrator: ingestion, query, index management, startup integrity checks.
- `config.py` -- Pydantic Settings from env vars. Cached via `lru_cache`.
- `agent/` -- planner, executor, intent classifier, tools, HyDE, query rewriter, decomposer, query expander.
- `ingestion/` -- LlamaParse cloud parser, file loader.
- `chunking/` -- window mode and semantic-hybrid mode.
- `indexing/` -- BM25 (Whoosh), vector (Chroma + NVIDIA embeddings), hybrid retriever (RRF), reranker.
- `generation/` -- LLM client with Groq/OpenRouter fallback chain, prompt templates.
- `validation/` -- citation presence and groundedness checks.
- `visualization/` -- knowledge graph builder with interactive subgraph and node detail extraction.
- `utils/` -- audit logger, index registry, job store, cache manager.

## Pages

| Page | URL | Purpose |
|------|-----|---------|
| Chat | `/chat` | Upload files, ask questions, get cited answers |
| Data Store | `/data-store` | Browse indexed chunks, view saved answers |
| Knowledge Graph | `/knowledge-graph` | Interactive force-directed graph with node inspector |
| Admin | `/admin` | Feature toggles, retrieval weights, provider status, index diagnostics |

## Advanced RAG Features (all ON by default)

- **HyDE** -- hypothetical document embeddings for better semantic matching
- **Query Rewrite** -- light (date resolution) + deep (LLM-based)
- **Query Decomposition** -- breaks multi-hop questions into sub-queries
- **Query Expansion** -- synonym/alternative formulations
- **Reranker** -- cross-encoder re-ranking of retrieved chunks
- **Hybrid Retrieval** -- BM25 + vector with Reciprocal Rank Fusion

## Observability

- Audit log: `output/logs/events.jsonl`
- Correlation: `request_id` (query), `job_id` (ingestion)
- LLM tracking: `_llm_provider`, `_llm_model`, `_llm_fallback_used`

## Verification

```bash
ruff check src api tests
pytest -q
python src/batch_runner.py data/sample_questions.json --eval --mode default \
  --max-invalid-rate 0.20 --max-p95-latency-ms 2500 --min-citation-hit-rate 0.80
```

## Docker

```bash
docker build -t rag-agent .
docker run -p 8000:8000 --env-file .env rag-agent
```
