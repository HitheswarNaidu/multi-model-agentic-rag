# Agent Pipeline Design

## End-to-End Flow

1. User uploads docs from Chat UI.
2. Pipeline queues ingestion job.
3. LlamaParse cloud API parses documents into blocks.
4. Parsed blocks are chunked and indexed (BM25 + vector).
   - Chunking mode can be `window` or `semantic_hybrid`.
5. User asks a question in Chat.
6. Intent classification -> query planning -> retrieval executes.
   - All advanced features (HyDE, reranker, decomposition, deep rewrite) ON by default.
7. LLM generation via Groq (primary) + OpenRouter (fallback) chain.
8. Validation and structured events are persisted.

## Modes

- `default`:
  - All advanced RAG features active (HyDE, reranker, decomposition, deep rewrite)
  - Hybrid retrieval (BM25 + vector with RRF fusion)
  - LLM fallback chain: Groq -> OpenRouter
- `deep`:
  - Same features, potentially with additional query expansion depth

## Diagnostics Model

- Human-friendly views in Data Store and Knowledge Graph.
- Expert mode reveals raw metadata and traces.
- Admin page centralizes runtime, provider status, and retrieval tuning.
- Knowledge Graph uses a simplified interaction model: minimal controls + node detail + why-related explanations + chat bridge.

## Failure Behavior

- LlamaParse API failure: ingestion blocked with clear error diagnostics.
- LLM provider quota failure: explicit `LLM_QUOTA_EXHAUSTED` with clear user-facing error.
- Summarization without provenance: blocked with `SUMMARY_PROVENANCE_MISSING`.
- Startup index integrity issues: flagged and auto-switched to latest clean index when possible.
