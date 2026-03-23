# Progress Snapshot

Date: 2026-03-22

## Completed: Provider Overhaul

- **BREAKING**: Replaced PyMuPDF/Docling/RapidOCR with LlamaParse cloud parser.
- **BREAKING**: Replaced SentenceTransformers with NVIDIA embedding API (`nvidia/llama-nemotron-embed-1b-v2`).
- **BREAKING**: Replaced Gemini LLM with Groq (primary) + OpenRouter (fallback) via configurable `LLM_FALLBACK_CHAIN`.
- All advanced RAG features (HyDE, query rewrite, decomposition, reranker) now ON by default.
- Vector retrieval now ON by default (`VECTOR_ENABLED=true`).
- Removed all Docling OCR configuration, PDF parse strategy controls, and Gemini references.
- Updated all documentation, requirements, and configuration files.

## Previously Completed: Chat-First Multipage Architecture

- Replaced single-page UI with chat-first multipage architecture.
- Added in-UI file upload and auto-queue indexing from Chat page.
- Restored dedicated Data Store and Knowledge Graph pages.
- Added Admin page with retrieval controls and provider status.
- Added semantic-hybrid chunking mode and semantic metadata.
- Added Knowledge Graph 3D mode (Plotly) and filtering controls.
- Interactive investigation KG mode (node detail, focus, hop expansion, chat bridge).
- Startup index integrity guard with auto-switch for demo/test indexes.
- Explicit quota hard-fail behavior (`LLM_QUOTA_EXHAUSTED`).
- Simplified Knowledge Graph UI to minimal controls.

## Current Expected UX

- Upload -> index -> ask from Chat page.
- Data and graph diagnostics available without leaving app context.
- Human default + expert-mode diagnostics.

## Operational Note

- Eval quality gate depends on corpus quality and provider behavior.
- Use `events.jsonl` plus eval artifacts for tuning and audits.
