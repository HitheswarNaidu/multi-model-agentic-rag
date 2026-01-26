# Multimodal Agentic RAG

Streamlit-based multimodal RAG with Docling parsing, smart chunking, hybrid retrieval (BM25 + vectors), Gemini LLM, and provenance-first answers.

## Quick Start
1. Create `.env` from `.env.example` and set `GEMINI_API_KEY` (optional for mocked runs).
2. Install deps: `pip install -r requirements.txt`.
3. Run app: `streamlit run app/main.py`.

### Typical Workflow
1. Upload documents in **Document Upload** page.
2. Click **Process & Index Uploads**.
3. Ask questions in **Query Interface**.
4. Inspect chunks and saved answers in **Data Store Viewer**.
5. View document/chunk connections in **Document Graph**.

### Running Tests
Run all tests:

`pytest -q`

E2E sanity is covered by `tests/test_e2e.py`.

## Layout
- `docs/` specifications, agent design, edge cases, progress
- `src/` core Python package
- `app/` Streamlit UI
- `data/` uploads/processed/indices (local)
- `output/` answers/logs
- `tests/` unit tests

## Features
- **Multimodal Parsing:** Docling-based extraction of text, tables, and layouts.
- **Precise Retrieval:** Row-level table chunking and hybrid search (BM25 + Vector) with **Cross-Encoder Reranking**.
- **Agentic Intelligence:**
    - **Clarification:** Detects vague queries and asks for scope.
    - **Intent Tuning:** Optimized for data/table lookup tasks.
- **Robustness:**
    - **Validation:** Numeric consistency checks (currency, units).
    - **Audit Logging:** Full execution traces in `output/logs/`.
- **Interactive UI:** Streamlit dashboard with Data Store filtering and Graph visualization.

## Status
Feature-complete. Includes robust validation, logging, and extensive testing logic.
