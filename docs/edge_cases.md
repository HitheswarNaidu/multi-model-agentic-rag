# Edge Cases

## Import Error at Startup

Symptom:

- `ModuleNotFoundError: No module named 'app'`

Mitigation:

- All Streamlit entry scripts now bootstrap root + `src` paths explicitly.
- Restart stale Streamlit process and hard refresh browser.

## LlamaParse API Failures

Symptom:

- Ingestion fails with `LLAMA_CLOUD_API_KEY` missing or invalid.

Behavior:

- Parser checks for API key before attempting parse.
- Clear error message with instructions to set the key in `.env`.

## Query Before Index Ready

- Chat page keeps index status visible.
- If user asks early, assistant returns guidance to finish indexing first.

## Partial Ingestion Failures

- Per-file failures are recorded in job status and logs.
- Successful files remain indexed.

## Provider Failures

- LLM fallback chain tries each provider in order (Groq -> OpenRouter).
- Error code is logged (`LLM_GENERATION_FAILED`) with request correlation.
- Quota failures are explicit (`LLM_QUOTA_EXHAUSTED`) and shown as user-facing error banners.
- When all providers exhausted, structured error returned (not silent fallback).

## Demo/Test Index Contamination

- Startup integrity check can detect suspicious catalogs (`doc1`, known demo markers).
- Runtime auto-switches to the latest clean index when available.
- If no clean index exists, integrity warning remains visible in Admin diagnostics.

## Summarize Returns Invalid

- Strict provenance is required for summaries.
- Missing summary citations now raise `SUMMARY_PROVENANCE_MISSING`.

## Large Knowledge Graphs

- Node cap defaults to 300 and warns when truncated.
- Use doc filter and node cap to reduce rendering load.
- 3D view intentionally avoids dense labels for readability.
