# Quickstart

## 1) Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2) Configure `.env`

Copy `.env.example` to `.env` and set your API keys:

```env
LLAMA_CLOUD_API_KEY=...       # LlamaParse document parsing
NVIDIA_API_KEY=...            # NVIDIA embedding API
GROQ_API_KEY=...              # Groq LLM (primary)
OPENROUTER_API_KEY=...        # OpenRouter LLM (fallback)
```

Default configuration (already set in `.env.example`):

```env
EMBEDDING_MODEL=nvidia/llama-nemotron-embed-1b-v2
VECTOR_ENABLED=true
LLM_FALLBACK_CHAIN=groq:openai/gpt-oss-120b,groq:openai/gpt-oss-20b,groq:llama-3.3-70b-versatile,groq:llama-3.1-8b-instant,openrouter:openrouter/free
HYDE_ENABLED=true
DEEP_REWRITE_ENABLED=true
DECOMPOSITION_ENABLED=true
RERANKER_ENABLED=true
CHUNKING_MODE=window
IGNORE_TEST_DEMO_INDEXES=true
```

With `IGNORE_TEST_DEMO_INDEXES=true` (default), startup auto-ignores suspicious demo/test indexes when a clean index is available.

## 3) Launch

```bash
run_app.bat
```

Optional full verify before launch:

```bash
run_app.bat --check
```

## 4) Use the App

1. Open `Chat` page.
2. Upload files in the UI.
3. Click `Upload + Start Indexing`.
4. Ask questions after index is ready.
   - For summaries, keep at least one document selected to enforce provenance.
5. Inspect Data Store / Knowledge Graph / Admin as needed.
   - In Knowledge Graph: use simple 3D/2D view, optionally filter by document, select a node, inspect details + why-related, and use `Ask Chat about this node`.

## 5) Verify

```bash
ruff check src app tests
pytest -q
python src/batch_runner.py data/sample_questions.json --eval --mode default --max-invalid-rate 0.20 --max-p95-latency-ms 2500 --min-citation-hit-rate 0.80
```
