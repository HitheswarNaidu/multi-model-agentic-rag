# System Specification

## Scope

Local Agentic RAG with chat-first UX, LlamaParse cloud parsing, and structured auditability.

## UI Architecture

Pages:

- `app/pages/1_💬_Chat.py` (primary)
- `app/pages/2_🗄️_Data_Store.py`
- `app/pages/3_🕸️_Knowledge_Graph.py`
- `app/pages/4_🛠️_Admin.py`

Knowledge Graph control contract:
- Minimal controls only (`3D/2D`, document filter, node cap, node selection).
- Node details must show what a node contains and why relationships exist.

Entry script:

- `app/main.py` (startup + redirect to Chat)

## Backend Interfaces

`src/rag/pipeline.py` public methods:

- `start_ingestion_job(...) -> str`
- `start_ingestion_job_for_uploads(uploaded_files, ...) -> dict`
- `get_ingestion_job(job_id) -> dict | None`
- `query_fast(question, filters=None, mode='default') -> dict`
- `query(...)` compatibility wrapper

Stable `query_fast` fields:

- `request_id`
- `timing_ms`
- `quality`
- `latency_ms` alias

## Retrieval Behavior

- All advanced RAG features ON by default:
  - reranker (cross-encoder)
  - HyDE (hypothetical document embeddings)
  - deep rewrite (LLM-based query rewriting)
  - decomposition (multi-hop query splitting)
- Hybrid retrieval: BM25 + Vector with RRF fusion (configurable weights).
- Summarization requires grounded provenance from retrieved chunk ids.
- Filters support `doc_id` and `doc_ids`.

## Provider Stack

- **Parsing:** LlamaParse cloud API via `LLAMA_CLOUD_API_KEY`.
- **Embeddings:** NVIDIA `nvidia/llama-nemotron-embed-1b-v2` via `NVIDIA_API_KEY`.
- **LLM:** Configurable fallback chain via `LLM_FALLBACK_CHAIN` (Groq primary, OpenRouter fallback).

## Index Integrity Contract

- `IGNORE_TEST_DEMO_INDEXES=true` enables startup detection of suspicious demo/test catalogs.
- Suspicious active indexes can be auto-switched to the latest clean version.
- No destructive deletion is performed by default (switch-first policy).

## Logging Contract

All runtime events in:

- `output/logs/events.jsonl`

Important events:

- `query_started`, `retrieval_finished`, `llm_finished`, `validation_finished`, `query_finished`
- `ingestion_job_started`, `ingestion_job_progress`, `ingestion_job_finished`, `ingestion_failed`
- `summary_provenance_missing`
- `index_integrity_checked`, `index_integrity_flagged`, `index_auto_switched`
- `kg_view_loaded`, `kg_node_selected`, `kg_subgraph_expanded`, `kg_filter_applied`, `kg_chat_bridge_invoked`

LLM provider tracking fields:

- `_llm_provider`
- `_llm_model`
- `_llm_fallback_used`
