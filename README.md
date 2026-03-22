# Multimodal Agentic RAG

Local, feature-rich Agentic RAG with a chat-first multipage Streamlit UI.

## What Changed

- UI is now multipage and chat-first:
  - `Chat`
  - `Data Store`
  - `Knowledge Graph`
  - `Admin`
- Upload happens directly in the Chat page (`st.file_uploader`) with auto-queued background indexing.
- Document parsing via LlamaParse cloud API (`LLAMA_CLOUD_API_KEY`).
- Vector retrieval ON by default (`VECTOR_ENABLED=true`) with NVIDIA embeddings (`nvidia/llama-nemotron-embed-1b-v2`).
- All advanced RAG features (HyDE, reranker, query rewrite, decomposition) ON by default.
- LLM via configurable fallback chain: Groq (primary) + OpenRouter (fallback) via `LLM_FALLBACK_CHAIN`.

## Run

```bash
run_app.bat
```

Full verification before launch:

```bash
run_app.bat --check
```

Direct fallback:

```bash
python -m streamlit run app/main.py
```

## Required API Keys

Set these in `.env`:

```env
LLAMA_CLOUD_API_KEY=...       # LlamaParse document parsing
NVIDIA_API_KEY=...            # NVIDIA embedding API (nvidia/llama-nemotron-embed-1b-v2)
GROQ_API_KEY=...              # Groq LLM (primary)
OPENROUTER_API_KEY=...        # OpenRouter LLM (fallback)
```

Optional configuration:

```env
LLM_FALLBACK_CHAIN=groq,openrouter   # Configurable provider chain
CHUNKING_MODE=window
IGNORE_TEST_DEMO_INDEXES=true
```

- `LLM_FALLBACK_CHAIN`: comma-separated list of LLM providers to try in order.
- `IGNORE_TEST_DEMO_INDEXES=true`: startup will auto-ignore/switch away from suspicious demo/test indexes.

## Runtime Guardrails

- Startup index integrity checks detect suspicious demo/test catalogs and auto-switch to the latest clean index when available.
- LLM quota failures are surfaced explicitly as `LLM_QUOTA_EXHAUSTED` (not silent/ambiguous).

## Vector/Embeddings Configuration

```env
VECTOR_ENABLED=true                                    # ON by default
EMBEDDING_MODEL=nvidia/llama-nemotron-embed-1b-v2     # NVIDIA embedding model
```

Vector retrieval is enabled by default using NVIDIA embeddings via API.
Set `VECTOR_ENABLED=false` to fall back to BM25-only retrieval.

## Architecture

- `app/main.py`: startup + redirect to Chat page.
- `app/pages/1_💬_Chat.py`: upload, indexing status, chat answers with citations.
- `app/pages/2_🗄️_Data_Store.py`: human/expert data inspection.
- `app/pages/3_🕸️_Knowledge_Graph.py`: interactive graph investigation workspace.
- Knowledge Graph supports a simplified `3D` and `2D` view with minimal controls:
  - layout toggle
  - document filter
  - node cap
  - node detail panel with “why related” explanations and ask-in-chat bridge
- `app/pages/4_🛠️_Admin.py`: provider status, retrieval toggles, maintenance.
- `src/rag/pipeline.py`: ingestion jobs, query orchestration, audit events.
- `src/rag/ingestion/parser.py`: LlamaParse cloud document parsing.

## Observability

Primary runtime log:

- `output/logs/events.jsonl`

Correlation IDs:

- query: `request_id`
- ingestion: `job_id`

Runtime events:

- `ingestion_failed`
- `kg_view_loaded`
- `kg_node_selected`
- `kg_subgraph_expanded`
- `kg_filter_applied`
- `kg_chat_bridge_invoked`
- `index_integrity_checked`
- `index_integrity_flagged`
- `index_auto_switched`

## Ingestion Benchmark (Parallel + Batched)

Use this to measure indexing throughput and gate regressions locally:

```bash
python src/batch_runner.py --benchmark-ingestion --benchmark-input-dir data/uploads --benchmark-repeats 3
```

With regression gate against a saved baseline report:

```bash
python src/batch_runner.py --benchmark-ingestion --benchmark-input-dir data/uploads --benchmark-baseline-file output/logs/ingestion_benchmark_BASELINE.json --max-ingestion-regression-pct 15
```

## Verification

```bash
ruff check src app tests
pytest -q
python src/batch_runner.py data/sample_questions.json --eval --mode default --max-invalid-rate 0.20 --max-p95-latency-ms 2500 --min-citation-hit-rate 0.80
```
