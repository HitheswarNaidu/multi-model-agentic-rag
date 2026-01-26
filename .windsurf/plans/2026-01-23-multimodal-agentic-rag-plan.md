# Multimodal Agentic RAG - Streamlit Implementation Plan

Build a complete Streamlit-based Multimodal Agentic RAG system with visual document analysis, hybrid retrieval, and interactive data store visualization.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create an intelligent RAG system for structured documents with a Streamlit dashboard showing document connections and data flow visually.

**Architecture:** Docling parsing → Smart chunking → Dual indexing (BM25 + Vector) → Agent planner → LLM generation → Validation layer, all visualized in Streamlit.

**Tech Stack:** Python 3.10+, Streamlit, Docling, Whoosh (BM25), ChromaDB, Sentence-Transformers, LangChain, Google Gemini (via Google AI Studio), NetworkX, Plotly, PyVis

---

## Project Structure

```
multimodal-rag-agentic/
├── pyproject.toml
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── docs/
│   ├── specs.md
│   ├── agent.md
│   └── plans/
│       └── 2026-01-23-multimodal-agentic-rag.md
├── src/
│   └── rag/
│       ├── __init__.py
│       ├── config.py
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   └── parser.py
│       ├── chunking/
│       │   ├── __init__.py
│       │   ├── chunker.py
│       │   └── metadata.py
│       ├── indexing/
│       │   ├── __init__.py
│       │   ├── bm25_index.py
│       │   ├── vector_store.py
│       │   └── hybrid_retriever.py
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── intent_classifier.py
│       │   ├── planner.py
│       │   ├── tools.py
│       │   └── executor.py
│       ├── generation/
│       │   ├── __init__.py
│       │   ├── llm_client.py
│       │   └── prompts.py
│       ├── validation/
│       │   ├── __init__.py
│       │   └── validator.py
│       └── visualization/
│           ├── __init__.py
│           ├── graph_builder.py
│           └── charts.py
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── pages/
│   │   ├── 1_📄_Document_Upload.py
│   │   ├── 2_🔍_Query_Interface.py
│   │   ├── 3_📊_Data_Store_Viewer.py
│   │   ├── 4_🕸️_Document_Graph.py
│   │   └── 5_⚙️_Settings.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── sidebar.py
│   │   ├── chunk_viewer.py
│   │   └── graph_viewer.py
│   └── utils/
│       ├── __init__.py
│       ├── session.py
│       └── styling.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_ingestion/
│   ├── test_chunking/
│   ├── test_indexing/
│   ├── test_agent/
│   └── test_validation/
├── data/
│   ├── uploads/
│   ├── processed/
│   └── indices/
├── output/
│   ├── answers/
│   └── logs/
└── notebooks/
    └── exploration.ipynb
```

---

## Phase 1: Project Setup

### Task 1.1: Initialize Project Structure
**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `README.md`

### Task 1.2: Create Base Package Structure
**Files:**
- Create: `src/rag/__init__.py`
- Create: `src/rag/config.py`
- Create: All `__init__.py` files in subpackages

### Task 1.3: Setup Testing Infrastructure
**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

---

## Phase 2: Ingestion Layer

### Task 2.1: Document Loader
**Files:**
- Create: `src/rag/ingestion/loader.py`
- Test: `tests/test_ingestion/test_loader.py`

**Functionality:**
- Load PDF, DOCX, images
- File validation and type detection
- Batch loading support

### Task 2.2: Document Parser (Docling)
**Files:**
- Create: `src/rag/ingestion/parser.py`
- Test: `tests/test_ingestion/test_parser.py`

**Functionality:**
- Docling integration
- Extract text, tables, figures
- Preserve layout and structure
- Return structured document blocks

---

## Phase 3: Smart Chunking Layer

### Task 3.1: Metadata Schema
**Files:**
- Create: `src/rag/chunking/metadata.py`
- Test: `tests/test_chunking/test_metadata.py`

**Schema:**
```python
@dataclass
class ChunkMetadata:
    doc_id: str
    doc_type: str
    page: int
    section: str
    chunk_id: str
    chunk_type: Literal["paragraph", "table", "row", "figure"]
    table_id: Optional[str]
    confidence: float
```

### Task 3.2: Smart Chunker
**Files:**
- Create: `src/rag/chunking/chunker.py`
- Test: `tests/test_chunking/test_chunker.py`

**Functionality:**
- Section-based chunking
- Table-aware chunking (full table + per-row)
- Figure + caption chunking
- Overlap windows
- Metadata-first format output

---

## Phase 4: Indexing Layer

### Task 4.1: BM25 Index (Whoosh)
**Files:**
- Create: `src/rag/indexing/bm25_index.py`
- Test: `tests/test_indexing/test_bm25.py`

**Functionality:**
- Create/update Whoosh index
- Search with metadata filters
- Return scored results

### Task 4.2: Vector Store (ChromaDB)
**Files:**
- Create: `src/rag/indexing/vector_store.py`
- Test: `tests/test_indexing/test_vector.py`

**Functionality:**
- Embed chunks with Sentence-Transformers
- Store in ChromaDB with metadata
- Similarity search with filters

### Task 4.3: Hybrid Retriever
**Files:**
- Create: `src/rag/indexing/hybrid_retriever.py`
- Test: `tests/test_indexing/test_hybrid.py`

**Functionality:**
- Reciprocal Rank Fusion
- Weighted scoring
- Metadata boosts
- Reranking option

---

## Phase 5: Agent Layer

### Task 5.1: Intent Classifier
**Files:**
- Create: `src/rag/agent/intent_classifier.py`
- Test: `tests/test_agent/test_intent.py`

**Query Types:**
- numeric_table
- definition
- multi_hop
- image_related

### Task 5.2: Agent Tools
**Files:**
- Create: `src/rag/agent/tools.py`
- Test: `tests/test_agent/test_tools.py`

**Tools:**
- bm25_search(query, filters)
- vector_search(query, filters)
- hybrid_search(query)
- table_row_search(query)
- rerank(candidates)
- call_llm(contexts)
- validate(answer)

### Task 5.3: Planner
**Files:**
- Create: `src/rag/agent/planner.py`
- Test: `tests/test_agent/test_planner.py`

**Logic:**
- Map intent → strategy
- Select tools
- Plan execution order

### Task 5.4: Executor
**Files:**
- Create: `src/rag/agent/executor.py`
- Test: `tests/test_agent/test_executor.py`

**Functionality:**
- Execute plan steps
- Handle retries
- Log all decisions

---

## Phase 6: Generation Layer

### Task 6.1: LLM Client
**Files:**
- Create: `src/rag/generation/llm_client.py`
- Test: `tests/test_generation/test_llm.py`

**Functionality:**
- Gemini (Google AI Studio) support with API key
- (Optional) Ollama stub for later
- Structured JSON output
- Provenance tracking

### Task 6.2: Prompt Templates
**Files:**
- Create: `src/rag/generation/prompts.py`

**Templates:**
- System prompt with rules
- Context injection template
- Structured output format

---

## Phase 7: Validation Layer

### Task 7.1: Answer Validator
**Files:**
- Create: `src/rag/validation/validator.py`
- Test: `tests/test_validation/test_validator.py`

**Checks:**
- Numeric sanity
- Provenance exists
- Conflict detection
- INSUFFICIENT_DATA fallback

---

## Phase 8: Visualization Layer

### Task 8.1: Graph Builder
**Files:**
- Create: `src/rag/visualization/graph_builder.py`

**Functionality:**
- Build NetworkX graph of documents and chunks
- Track connections (same doc, cross-doc references)
- Node attributes (type, page, section)

### Task 8.2: Chart Generators
**Files:**
- Create: `src/rag/visualization/charts.py`

**Charts:**
- Chunk distribution by type (Plotly)
- Document stats
- Retrieval score distributions
- Query flow visualization

---

## Phase 9: Streamlit Dashboard

### Task 9.1: Main App Entry
**Files:**
- Create: `app/main.py`
- Create: `app/utils/session.py`
- Create: `app/utils/styling.py`

### Task 9.2: Sidebar Component
**Files:**
- Create: `app/components/sidebar.py`

**Features:**
- Document list
- Filter controls
- Settings shortcuts

### Task 9.3: Document Upload Page
**Files:**
- Create: `app/pages/1_📄_Document_Upload.py`

**Features:**
- Drag-drop upload
- Processing progress
- Preview parsed structure
- Chunking visualization

### Task 9.4: Query Interface Page
**Files:**
- Create: `app/pages/2_🔍_Query_Interface.py`

**Features:**
- Query input
- Strategy selection (auto/manual)
- Results with provenance
- Agent decision log

### Task 9.5: Data Store Viewer Page
**Files:**
- Create: `app/pages/3_📊_Data_Store_Viewer.py`

**Features:**
- BM25 index browser
- Vector store explorer
- Chunk metadata table
- Search within index
- Saved outputs browser (from `output/answers`)

### Task 9.6: Document Graph Page (Visual Connections)
**Files:**
- Create: `app/pages/4_🕸️_Document_Graph.py`
- Create: `app/components/graph_viewer.py`

**Features:**
- Interactive PyVis graph
- Document nodes (color by type)
- Chunk nodes (nested under docs)
- Cross-document connections
- Zoom/pan/filter
- Click node for details

### Task 9.7: Settings Page
**Files:**
- Create: `app/pages/5_⚙️_Settings.py`

**Features:**
- LLM provider config (Gemini API key)
- Embedding model selection (default `all-mpnet-base-v2`)
- Chunking parameters
- Retrieval weights

---

## Phase 10: Integration & Testing

### Task 10.1: End-to-End Pipeline
**Files:**
- Create: `src/rag/pipeline.py`
- Test: `tests/test_e2e.py`

**Additions:**
- Ensure outputs saved to `output/answers` and `output/logs`

### Task 10.2: Sample Documents
**Files:**
- Add sample PDFs to `data/uploads/`

---

## Phase 11: Documentation & Polish

### Task 11.1: README
- Installation instructions
- Quick start
- Configuration guide

### Task 11.2: Edge Cases & RAG Pitfalls
**Files:**
- Create: `docs/edge_cases.md`

**Content:**
- Common RAG issues (hallucination, sparse numeric hits, table misalignment, vague queries)
- Agentic orchestration failure modes (tool loops, missing validation)
- Mitigations (retrieval fallback, re-querying, metadata filters, provenance checks)

### Task 11.3: Progress Tracking
**Files:**
- Create: `docs/progress.md`

---

## Dependencies (requirements.txt)

```
# Core
python-dotenv>=1.0.0
pydantic>=2.0.0

# Document Processing
docling>=1.0.0
pymupdf>=1.23.0
python-docx>=0.8.11
pillow>=10.0.0

# Indexing
whoosh>=2.7.4
chromadb>=0.4.0
sentence-transformers>=2.2.0

# Agent & LLM
langchain>=0.1.0
langchain-google-genai>=1.0.0
langchain-community>=0.0.10
google-generativeai>=0.3.0

# Streamlit Dashboard
streamlit>=1.30.0
streamlit-option-menu>=0.3.6

# Visualization
plotly>=5.18.0
pyvis>=0.3.2
networkx>=3.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0

# Dev
black>=23.0.0
ruff>=0.1.0
mypy>=1.0.0
```

---

## Execution Order

1. **Phase 1** - Setup (Tasks 1.1-1.3)
2. **Phase 2** - Ingestion (Tasks 2.1-2.2)
3. **Phase 3** - Chunking (Tasks 3.1-3.2)
4. **Phase 4** - Indexing (Tasks 4.1-4.3)
5. **Phase 5** - Agent (Tasks 5.1-5.4)
6. **Phase 6** - Generation (Tasks 6.1-6.2)
7. **Phase 7** - Validation (Task 7.1)
8. **Phase 8** - Visualization (Tasks 8.1-8.2)
9. **Phase 9** - Streamlit (Tasks 9.1-9.7)
10. **Phase 10** - Integration (Tasks 10.1-10.2)
11. **Phase 11** - Documentation (Tasks 11.1-11.2)

---

## Visual Dashboard Features Summary

| Page | Key Visual Elements |
|------|---------------------|
| Document Upload | Progress bars, parsed structure tree, chunk preview cards |
| Query Interface | Agent decision flow diagram, retrieval scores bar chart, provenance links |
| Data Store Viewer | Interactive tables, chunk type pie chart, embedding 2D projection |
| Document Graph | Interactive node graph (PyVis), document clusters, cross-doc edges |
| Settings | Configuration forms, connection status indicators |

---

## Questions Before Proceeding

1. **LLM Provider:** Gemini via Google AI Studio ✅
2. **Embedding Model:** `all-mpnet-base-v2` (accurate) ✅
3. **Sample Documents:** Do you have specific PDFs/docs to test with?
4. **Auth/Multi-user:** Single-user local app ✅
5. **Persistence:** File-based; outputs in `output/answers` and `output/logs` ✅

