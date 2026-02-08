# Agent Pipeline Design

## End-to-End Flow

1. User uploads docs from Chat UI.
2. Pipeline queues ingestion job.
3. Strict OCR preflight validates Docling assets.
4. Parsed blocks are chunked and indexed (BM25 + vector).
   - Chunking mode can be `window` or `semantic_hybrid`.
   - PDF parsing strategy can be `fast_text_first`, `docling_first`, or `race`.
   - Non-strict Docling OCR can be enabled with `DOCLING_OCR_AUTO=true`.
5. User asks a question in Chat.
6. Query rewrite/planning/retrieval executes by selected mode.
7. One generation call returns answer + citations.
8. Validation and structured events are persisted.

## Modes

- `default`:
  - deterministic date rewrite
  - fast retrieval path
  - reranker/HyDE/decomposition/deep rewrite disabled
- `deep`:
  - optional advanced features from Admin toggles

## Diagnostics Model

- Human-friendly views in Data Store and Knowledge Graph.
- Expert mode reveals raw metadata and traces.
- Admin page centralizes runtime, OCR, and retrieval tuning.
- Knowledge Graph uses a simplified interaction model: minimal controls + node detail + why-related explanations + chat bridge.

## Failure Behavior

- OCR config failure: ingestion blocked with `OCR_CONFIG_INVALID`.
- LLM provider quota failure: explicit `LLM_QUOTA_EXHAUSTED` with clear user-facing error.
- Summarization without provenance: blocked with `SUMMARY_PROVENANCE_MISSING`.
- Startup index integrity issues: flagged and auto-switched to latest clean index when possible.
