# CLAUDE

Operational guidance for coding agents in this repository.

## Current UX Contract

- Multipage Streamlit app with Chat as primary entry.
- Users upload files directly in Chat UI.
- Data Store and Knowledge Graph remain first-class diagnostic pages.
- Knowledge Graph is an interactive investigation workflow, not just static visualization.
- Knowledge Graph controls should stay minimal and avoid dropdown-heavy advanced modes by default.
- Admin page hosts OCR validation and runtime/retrieval controls.

## Retrieval/Reasoning Defaults

- `mode=default`: fast-first, light date rewrite, reranker off, HyDE off.
- `mode=deep`: advanced helpers available only when enabled in Admin.
- Quota failures must be explicit: surface `LLM_QUOTA_EXHAUSTED` rather than ambiguous fallback.

## OCR Policy

- Strict Docling OCR is optional (`DOCLING_OCR_FORCE=false` default).
- Missing model paths are blocking ingestion errors (`OCR_CONFIG_INVALID`).
- No silent fallback when strict mode is enabled.
- Non-strict PDF parsing uses `PDF_PARSE_STRATEGY` (default: `fast_text_first`) for low-latency indexing.
- Non-strict Docling parsing can still use OCR via `DOCLING_OCR_AUTO=true` for scanned/low-text PDFs.

## Vector Policy

- Vector retrieval/embeddings are optional (`VECTOR_ENABLED=false` default).
- BM25-only mode is supported and should not crash on legacy Chroma embedding conflicts.

## Auditability

- Structured events are required in `output/logs/events.jsonl`.
- Always include `request_id` for query and `job_id` for ingestion.
- Capture timing and quality fields for post-run audits.
- Parser strategy observability is required (`parser_strategy_selected`, `parser_fallback_used`).
- Index integrity observability is required (`index_integrity_checked`, `index_integrity_flagged`, `index_auto_switched`).

## Verification Commands

```bash
ruff check src app tests
pytest -q
python src/batch_runner.py data/sample_questions.json --eval --mode default --max-invalid-rate 0.20 --max-p95-latency-ms 2500 --min-citation-hit-rate 0.80
```
