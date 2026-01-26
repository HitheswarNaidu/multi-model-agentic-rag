# Changelog

## [0.2.0] - 2026-01-26

### Added
- **Clarification Intent:** The agent now detects vague queries (e.g., "data") and prompts the LLM to ask clarifying questions.
- **Audit Logging:** Full execution logs (plan, intent, retrieval, validation) are now saved to `output/logs/`.
- **Data Store Filtering:** Users can now filter chunks by `doc_id` and `chunk_type` in the Streamlit "Data Store Viewer".
- **Validation Logic:** Enhanced numeric validation to handle trailing dots (`100.`) and prefix currency symbols (`$500`).
- **Setup Script:** Added `verify_setup.py` for environment diagnostics.

### Changed
- **Table Chunking:** Refactored `src/rag/chunking/chunker.py` to split `table` blocks into individual `row` chunks for precise retrieval.
- **Retrieval Filtering:** Updated `BM25Index`, `VectorStore`, and `HybridRetriever` to strictly respect `chunk_type` filters (critical for table row search).
- **Prompt Engineering:** Updated `src/rag/generation/prompts.py` to enforce strict JSON output and include conflict detection flags.
- **Dependencies:** Added `pandas` and `pydantic-settings` to `requirements.txt`.

### Fixed
- Fixed bug where `table_row_search` tool failed to filter by `chunk_type`.
- Fixed potential crash in Docling parser by adding fallback logging.
- Fixed `test_validator_logic.py` to correctly test unit mismatches.

### Tests
- Added `tests/test_real_logic.py` for core logic verification.
- Added `tests/test_validator_logic.py` for validation robustness.
- Added `tests/test_full_architecture.py` for end-to-end architecture mocking.
