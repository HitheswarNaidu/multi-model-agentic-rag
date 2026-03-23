# Changelog

## [0.3.0] - Next.js Frontend + FastAPI Backend

### Added
- Next.js 14 App Router frontend (`frontend/`) with shadcn/ui v4 + Tailwind CSS v4
- Graphite dark theme (near-black #1A1A1A + burnt orange #E8590C accent)
- FastAPI backend (`api/server.py`) with 16 REST endpoints wrapping Pipeline
- SSE streaming for `/api/query` endpoint
- Chat page: message bubbles with citations, file upload, Fast/Deep mode toggle, stats cards
- Data Store page: TanStack Table chunk browser with filters/pagination, saved answers
- Knowledge Graph page: canvas force-directed graph with node inspector
- Admin page: feature toggles, retrieval weight sliders, provider status, index diagnostics
- API client (`frontend/lib/api.ts`) and hooks (`use-chat.ts`, `use-ingestion.ts`)
- Sidebar navigation with Workspace/System sections

### Changed
- Primary UI is now Next.js (port 3000) instead of Streamlit (port 8501)
- Dockerfile now runs FastAPI instead of Streamlit
- `run_app.bat` starts both FastAPI backend and Next.js frontend
- `verify_setup.py` checks for fastapi/uvicorn instead of streamlit
- `pyproject.toml` updated to v0.2.0, Streamlit moved to optional deps
- Graph logic (`build_interactive_subgraph`, `get_node_detail`) extracted from Streamlit component to `src/rag/visualization/graph_builder.py`

### Removed
- `streamlit-option-menu` dependency (unused)
- `black`, `mypy` from main deps (moved to optional dev deps)
- Design preview artifacts (`design-preview/`, palette PNGs)
- Nested `frontend/.git/` directory
- `STREAMLIT_PORT` env var from `.env.example`

### Fixed
- 3 test files (`test_kg_interaction_flow`, `test_kg_performance_guardrails`) now import from `rag.visualization.graph_builder` instead of Streamlit components
- `test_graph_state_bridge` skipped (Streamlit session state legacy)

## [Unreleased - prior]

### Changed
- Replaced PyMuPDF/Docling/RapidOCR with LlamaParse cloud parser
- Replaced SentenceTransformers embeddings with NVIDIA embedding API
- Replaced Gemini LLM with Groq (primary) + OpenRouter (fallback) via LLM_FALLBACK_CHAIN
- All advanced RAG features (HyDE, rewrite, decomposition, reranker) ON by default
- Vector retrieval ON by default (VECTOR_ENABLED=true)

## [0.2.0] - Chat-First Multipage Architecture

### Added
- Chat-first multipage Streamlit UI (Chat, Data Store, Knowledge Graph, Admin)
- Upload flow with automatic background indexing queue
- Knowledge Graph 3D/2D modes with interactive investigation
- Startup index integrity guard with auto-switch
- Semantic-hybrid chunking option

### Changed
- `app/main.py` boots and redirects to Chat page
- Deep helpers (HyDE, rewrite, decomposition) explicitly toggleable

### Removed
- Single-page monolithic UI flow
