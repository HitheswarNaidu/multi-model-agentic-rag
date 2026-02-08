# Gemini Integration Notes

## Runtime

- LLM client: `src/rag/generation/llm_client.py`
- Default answer path: single generation call in `mode=default`
- Deep behaviors remain optional and toggleable in Admin

## Config

Set in `.env`:

```env
GEMINI_API_KEY=your_api_key
```

If key is missing, the app runs with mock fallback behavior.

## UI Surfaces

Gemini-backed answers are shown in:

- `app/pages/1_💬_Chat.py`
- graph selections from `app/pages/3_🕸️_Knowledge_Graph.py` can scope chat queries.
- Knowledge Graph UI is intentionally minimal (simple 3D/2D + node details + ask-in-chat).

with citations, latency, validation, and optional internals.

## Failure Behavior

Provider failures return structured fallback payloads and log error events to:

- `output/logs/events.jsonl`

Key error code:

- `LLM_GENERATION_FAILED`
- `LLM_QUOTA_EXHAUSTED` (provider 429 / `RESOURCE_EXHAUSTED`)
- `SUMMARY_PROVENANCE_MISSING` (summarization with missing citations/provenance)

Model payload parsing supports JSON code fences and malformed JSON fallback with:

- `LLM_RESPONSE_PARSE_FAILED`

## Debugging

1. Confirm `GEMINI_API_KEY` is set.
2. Check `events.jsonl` for `query_started`, `llm_finished`, `error`, `query_finished`.
3. Correlate via `request_id`.
4. For OCR-heavy/scanned PDFs, keep `DOCLING_OCR_AUTO=true` (or strict OCR with validated model paths).
