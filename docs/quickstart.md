# Quickstart

## 1) Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2) Configure `.env`

Minimum:

```env
GEMINI_API_KEY=
EMBEDDING_MODEL=all-mpnet-base-v2
VECTOR_ENABLED=false
DOCLING_OCR_FORCE=false
PDF_PARSE_STRATEGY=fast_text_first
PDF_TEXT_MIN_CHARS=300
CHUNKING_MODE=window
DOCLING_OCR_AUTO=true
IGNORE_TEST_DEMO_INDEXES=true
```

Enable strict OCR only if you have all RapidOCR assets:

```env
DOCLING_OCR_FORCE=true
DOCLING_OCR_DET_MODEL_PATH=...
DOCLING_OCR_CLS_MODEL_PATH=...
DOCLING_OCR_REC_MODEL_PATH=...
DOCLING_OCR_REC_KEYS_PATH=...
DOCLING_OCR_FONT_PATH=...
```

With `DOCLING_OCR_AUTO=true` (default), non-strict runs will still attempt Docling OCR on scanned/low-text PDFs when Docling parser path is used.
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
