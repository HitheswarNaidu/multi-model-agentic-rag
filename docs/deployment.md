# Deployment (Local Desktop)

## Entry Point

Use:

```bash
run_app.bat
```

For full setup import validation:

```bash
run_app.bat --check
```

## Runtime Shape

- Streamlit multipage app
- Chat-first interaction model
- Data Store and Knowledge Graph diagnostics
- Admin operations and provider controls
- Hybrid retrieval ON by default (BM25 + Vector with NVIDIA embeddings)
- Knowledge Graph supports 2D and 3D rendering modes.
- Knowledge Graph includes minimal controls (view mode, document filter, node cap, node selection).

## Required API Keys

Set in `.env`:

```env
LLAMA_CLOUD_API_KEY=...       # LlamaParse document parsing
NVIDIA_API_KEY=...            # NVIDIA embedding API
GROQ_API_KEY=...              # Groq LLM (primary)
OPENROUTER_API_KEY=...        # OpenRouter LLM (fallback)
```

## Parser and Chunking Defaults

- `CHUNKING_MODE=window` (or `semantic_hybrid`)
- `IGNORE_TEST_DEMO_INDEXES=true` (startup index integrity guard + clean-index auto-switch)
- All advanced RAG features ON by default (HyDE, reranker, decomposition, deep rewrite)

## Stale Process Troubleshooting

1. Stop existing Streamlit processes.
2. Run `run_app.bat` again.
3. Hard refresh browser.
4. If needed, clear `app/__pycache__`.

## Release Gate

```bash
ruff check src app tests
pytest -q
python src/batch_runner.py data/sample_questions.json --eval --mode default --max-invalid-rate 0.20 --max-p95-latency-ms 2500 --min-citation-hit-rate 0.80
```
