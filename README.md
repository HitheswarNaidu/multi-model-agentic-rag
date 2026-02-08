# Multimodal Agentic RAG

Local, feature-rich Agentic RAG with a chat-first multipage Streamlit UI.

## What Changed

- UI is now multipage and chat-first:
  - `Chat`
  - `Data Store`
  - `Knowledge Graph`
  - `Admin`
- Upload happens directly in the Chat page (`st.file_uploader`) with auto-queued background indexing.
- OCR strict mode is optional (`DOCLING_OCR_FORCE=false` by default).
- PDF parsing strategy is configurable (`PDF_PARSE_STRATEGY=fast_text_first` default).
- Vector retrieval/embeddings are optional (`VECTOR_ENABLED=false` by default, BM25-only mode).
- Fast path remains default; deep features (HyDE, reranker, deep rewrite, decomposition) are admin-controlled.

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

## Optional OCR Configuration

Set these in `.env` only if you enable strict OCR mode:

```env
DOCLING_OCR_FORCE=true
DOCLING_OCR_DET_MODEL_PATH=...
DOCLING_OCR_CLS_MODEL_PATH=...
DOCLING_OCR_REC_MODEL_PATH=...
DOCLING_OCR_REC_KEYS_PATH=...
DOCLING_OCR_FONT_PATH=...
```

If strict mode is enabled and paths are missing/invalid, ingestion fails with
`OCR_CONFIG_INVALID` and a missing-path list.

Optional parser/chunking controls:

```env
PDF_PARSE_STRATEGY=fast_text_first
PDF_TEXT_MIN_CHARS=300
CHUNKING_MODE=window
DOCLING_OCR_AUTO=true
IGNORE_TEST_DEMO_INDEXES=true
```

- `fast_text_first`: uses PyMuPDF first for speed, falls back to Docling when needed.
- `docling_first`: preserves legacy behavior.
- `race`: attempts both and picks the better extraction.
- `DOCLING_OCR_AUTO=true`: in non-strict mode, Docling OCR is attempted when Docling parser path is used (helps scanned/image PDFs).
- `IGNORE_TEST_DEMO_INDEXES=true`: startup will auto-ignore/switch away from suspicious demo/test indexes.

## Runtime Guardrails

- Startup index integrity checks detect suspicious demo/test catalogs and auto-switch to the latest clean index when available.
- LLM quota failures are surfaced explicitly as `LLM_QUOTA_EXHAUSTED` (not silent/ambiguous).

## Optional Vector/Embeddings Configuration

```env
VECTOR_ENABLED=false
EMBEDDING_MODEL=all-mpnet-base-v2
```

When `VECTOR_ENABLED=false`, the app uses BM25-only retrieval and does not require
embedding initialization.

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
- `app/pages/4_🛠️_Admin.py`: OCR validation, retrieval toggles, maintenance.
- `src/rag/pipeline.py`: ingestion jobs, query orchestration, audit events.
- `src/rag/ingestion/parser.py`: strict Docling OCR preflight + typed OCR errors.

## Observability

Primary runtime log:

- `output/logs/events.jsonl`

Correlation IDs:

- query: `request_id`
- ingestion: `job_id`

OCR events:

- `ocr_config_validated`
- `ocr_config_error`
- `ingestion_failed`
- `parser_strategy_selected`
- `parser_fallback_used`
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
