# Multimodal Agentic RAG Context

## Project Overview
This project is a **Multimodal Agentic RAG (Retrieval Augmented Generation)** system designed to process and query structured documents like PDFs, invoices, and reports. It goes beyond simple text extraction by preserving layout, tables, and contextual information.

**Key Features:**
*   **Multimodal Parsing:** Uses `Docling` to understand document structure (tables, figures, layout).
*   **Smart Chunking:** Metadata-aware chunking strategies (section-based, table-aware).
*   **Hybrid Retrieval:** Combines BM25 (keyword) and Vector Search (semantic) for better accuracy.
*   **Agentic Reasoning:** An agent layer plans retrieval strategies based on the user query.
*   **Gemini Integration:** Uses Google's Gemini models for answer generation and reasoning.
*   **Interactive UI:** A Streamlit dashboard for uploading documents, visualizing the knowledge graph, and querying.

## Architecture

### Directory Structure
*   `src/rag/`: Core logic package.
    *   `ingestion/`: Document parsing (Docling).
    *   `chunking/`: Smart chunking logic.
    *   `indexing/`: Management of BM25 and Vector indices.
    *   `agent/`: Agentic planning and reasoning.
    *   `generation/`: LLM interaction (Gemini).
    *   `pipeline.py`: Main orchestration.
    *   `config.py`: Configuration management.
*   `app/`: Streamlit frontend application.
    *   `pages/`: Individual UI pages (Upload, Query, Viewer, Graph, Settings).
*   `data/`: Local storage for uploads, processed data, and indices.
*   `docs/`: detailed documentation and specifications.
*   `tests/`: Unit and end-to-end tests.

### Tech Stack
*   **Language:** Python 3.10+
*   **Frameworks:** Streamlit, LangChain, Pydantic
*   **AI/ML:** Google Gemini (via `google-genai` / `langchain-google-genai`), Sentence Transformers
*   **Retrieval:** ChromaDB (Vector), Whoosh (BM25)
*   **Parsing:** Docling
*   **Tools:** Ruff, Black, Mypy, Pytest

## Setup & Usage

### 1. Environment Configuration
The project uses `pydantic-settings` and requires a `.env` file in the root directory.
*   Copy `.env.example` to `.env`.
*   Set `GEMINI_API_KEY` (Required for generation).
*   Other settings (defaults in `src/rag/config.py`): `EMBEDDING_MODEL`, `STREAMLIT_PORT`.

### 2. Installation
```bash
pip install -r requirements.txt
```

### 3. Running the Application
Start the Streamlit dashboard:
```bash
streamlit run app/main.py
```

### 4. Running Tests
Run the test suite using `pytest`:
```bash
pytest
```
*   `tests/test_e2e.py` contains sanity checks.

## Development Conventions

*   **Code Style:** Adhere to `black` (formatting) and `ruff` (linting) standards.
*   **Typing:** Use type hints; checking is enforced via `mypy`.
*   **Testing:** New features must include unit tests. Use `pytest` fixtures where appropriate.
*   **Documentation:** Update `docs/` when changing core architectural components.
