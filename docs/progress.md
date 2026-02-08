# Progress Snapshot

Date: 2026-02-07

## Completed in This Iteration

- Replaced single-page UI with chat-first multipage architecture.
- Added in-UI file upload and auto-queue indexing from Chat page.
- Restored dedicated Data Store and Knowledge Graph pages.
- Added Admin page with OCR validation and retrieval controls.
- Implemented strict Docling OCR preflight with typed blocking errors.
- Added uploaded-file ingestion entrypoint and richer metadata persistence.
- Updated docs to match new IA and OCR policy.
- Added fast PDF parser strategy with fallback observability events.
- Added semantic-hybrid chunking mode and semantic metadata.
- Added Knowledge Graph 3D mode (Plotly) and filtering controls.
- Fixed summarize provenance failures with strict citation guardrails.
- Upgraded Knowledge Graph to interactive investigation mode with:
  - node selection/detail panel
  - focus mode and hop expansion
  - edge-type filtering
  - path explorer
  - chat bridge actions
- Improved Docling OCR reliability in non-strict mode via best-effort OCR path for scanned/low-text PDFs.
- Added startup index integrity guard to auto-switch away from suspicious demo/test indexes.
- Added explicit quota hard-fail behavior (`LLM_QUOTA_EXHAUSTED`) with Chat banner visibility.
- Simplified Knowledge Graph UI to minimal controls and cleaner normal 3D rendering.

## Current Expected UX

- Upload -> index -> ask from Chat page.
- Data and graph diagnostics available without leaving app context.
- Human default + expert-mode diagnostics.

## Operational Note

- Eval quality gate depends on corpus quality and provider behavior.
- Use `events.jsonl` plus eval artifacts for tuning and audits.
