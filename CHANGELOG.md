# Changelog

## [Unreleased]

### Added
- Chat-first multipage Streamlit IA:
  - `app/pages/1_💬_Chat.py`
  - `app/pages/2_🗄️_Data_Store.py`
  - `app/pages/3_🕸️_Knowledge_Graph.py`
  - `app/pages/4_🛠️_Admin.py`
- UI upload flow with automatic background indexing queue.
- Strict Docling OCR configuration validator with typed `OCR_CONFIG_INVALID` failures.
- Admin OCR test panel and actionable missing-asset diagnostics.
- Query feature-flag audit fields (`hyde`, reranker, deep rewrite, decomposition).
- Richer chunk metadata persistence (`source_hash`, `ingest_timestamp_utc`, table/image flags).
- PDF parser strategy controls (`fast_text_first`, `docling_first`, `race`) with parser fallback events.
- Semantic-hybrid chunking option with semantic metadata fields.
- Knowledge Graph 3D mode (Plotly) with filtering and node-cap controls.
- Investigation-first interactive Knowledge Graph:
  - side-panel node details
  - focus mode + hop-depth expansion
  - edge-type filters (doc-chunk/semantic/same-page/doc-similarity)
  - path explorer
  - chat bridge from selected node context
- Strict summary provenance guardrail (`SUMMARY_PROVENANCE_MISSING`) and summary provenance event.
- Startup index integrity guard with suspicious-index detection and auto-switch to latest clean index.
- Admin index integrity diagnostics with one-click switch to latest clean index.

### Changed
- `app/main.py` now boots and redirects to Chat page.
- `src/rag/pipeline.py` supports uploaded-file ingestion entrypoint and per-query feature flag logging.
- `src/rag/agent/planner.py` deep helpers are explicitly toggleable.
- `src/rag/agent/query_rewriter.py` supports deep rewrite gating.
- Summarization retrieval now uses real document chunks instead of synthetic summary chunks.
- Chat document filtering now supports multi-doc filters (`doc_ids`).
- Knowledge Graph controls were simplified to a minimal flow (layout + document + node cap + node details).

### Removed
- Previous single-page monolithic UI flow.

### Fixed
- Eliminated stale `ModuleNotFoundError: No module named 'app'` risk by consistent path bootstrap in page entrypoints.
- Stopped noisy repeated OCR warnings by preflight validation and fail-fast ingestion behavior.
- Fixed fenced-JSON parsing from model outputs to preserve provenance/citation flow.
- Fixed Docling OCR reliability for scanned/low-text PDFs in non-strict mode by enabling best-effort OCR when the parser reaches Docling.
- Fixed ambiguous quota behavior by mapping Gemini 429/RESOURCE_EXHAUSTED to explicit `LLM_QUOTA_EXHAUSTED`.
- Added Chat quota banner and document-filter reload hint after indexing completion to reduce stale-state confusion.
- Simplified 3D graph rendering to a normal, uncluttered mode and removed advanced dropdown-heavy KG controls.
