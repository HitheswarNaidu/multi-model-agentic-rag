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
- Admin operations and OCR controls
- BM25-only retrieval by default (`VECTOR_ENABLED=false`)
- Knowledge Graph supports 2D and 3D rendering modes.
- Knowledge Graph includes minimal controls (view mode, document filter, node cap, node selection).

## OCR Asset Paths (Only for Strict OCR Mode)

Strict OCR mode is optional. Only when `DOCLING_OCR_FORCE=true`, set:

- `DOCLING_OCR_DET_MODEL_PATH`
- `DOCLING_OCR_CLS_MODEL_PATH`
- `DOCLING_OCR_REC_MODEL_PATH`
- `DOCLING_OCR_REC_KEYS_PATH`
- `DOCLING_OCR_FONT_PATH`

If invalid/missing, ingestion fails fast with clear diagnostics.

## Parser and Chunking Defaults

- `PDF_PARSE_STRATEGY=fast_text_first`
- `PDF_TEXT_MIN_CHARS=300`
- `CHUNKING_MODE=window`
- `DOCLING_OCR_AUTO=true` (best-effort OCR in non-strict Docling parser flow)
- `IGNORE_TEST_DEMO_INDEXES=true` (startup index integrity guard + clean-index auto-switch)

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
