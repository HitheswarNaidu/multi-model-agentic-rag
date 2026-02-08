# Edge Cases

## Import Error at Startup

Symptom:

- `ModuleNotFoundError: No module named 'app'`

Mitigation:

- All Streamlit entry scripts now bootstrap root + `src` paths explicitly.
- Restart stale Streamlit process and hard refresh browser.

## OCR Asset Misconfiguration

Symptom:

- Ingestion fails quickly with `OCR_CONFIG_INVALID`.

Behavior:

- No silent fallback when strict OCR is enabled.
- Missing env vars and missing files are surfaced clearly in Admin and job status.

## OCR Misses on Scanned PDFs (Non-Strict Mode)

- Keep `DOCLING_OCR_AUTO=true` so Docling parser path attempts OCR for low-text/scanned PDFs.
- Check `parser_strategy_selected` events for `ocr_enabled=true` when validating behavior.

## Query Before Index Ready

- Chat page keeps index status visible.
- If user asks early, assistant returns guidance to finish indexing first.

## Partial Ingestion Failures

- Per-file failures are recorded in job status and logs.
- Successful files remain indexed.

## Provider Failures

- Query still returns structured fallback answer.
- Error code is logged (`LLM_GENERATION_FAILED`) with request correlation.
- Quota failures are explicit (`LLM_QUOTA_EXHAUSTED`) and shown as user-facing error banners.

## Demo/Test Index Contamination

- Startup integrity check can detect suspicious catalogs (`doc1`, known demo markers).
- Runtime auto-switches to the latest clean index when available.
- If no clean index exists, integrity warning remains visible in Admin diagnostics.

## Slow PDF Ingestion

- Default strategy is `fast_text_first` to avoid Docling-only latency spikes.
- Fallback behavior is logged via `parser_strategy_selected` and `parser_fallback_used`.

## Summarize Returns Invalid

- Strict provenance is required for summaries.
- Missing summary citations now raise `SUMMARY_PROVENANCE_MISSING`.

## Large Knowledge Graphs

- Node cap defaults to 300 and warns when truncated.
- Use doc filter and node cap to reduce rendering load.
- 3D view intentionally avoids dense labels for readability.
