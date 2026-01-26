# Quickstart

## 1) Environment
- Python 3.13 (tested), Windows.
- Create/activate venv:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
- Install deps:
  ```powershell
  pip install -r requirements.txt
  ```

## 2) Configure
Create `.env` (or set env vars):
```
GEMINI_API_KEY=your_key_here   # leave empty to use mock LLM
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## 3) Cache models (offline-friendly)
- Embeddings (MiniLM) are already cached under `%USERPROFILE%\.cache\huggingface\hub`. If needed, prewarm:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
  ```
- RapidOCR (Option A: default cache):
  ```powershell
  $env:RAPIDOCR_HOME="$env:USERPROFILE\.rapidocr"
  .\.venv\Scripts\Activate.ps1
  python -c "from rapidocr_onnxruntime import RapidOCR; o=RapidOCR(); print(getattr(o, 'model_dir', 'model_dir not exposed'))"
  ```
  This downloads PP-OCRv4 det/rec/cls models into `%USERPROFILE%\.rapidocr`.

## 4) Run the app
```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app/main.py --server.fileWatcherType none
```
Open http://localhost:8501.

## 5) Workflow
- Place files in `data/uploads/`.
- In **Document Upload** page, click **Index data/uploads** to build BM25/vector/hybrid indices.
- In **Query Interface**, select a document (or All) and ask a question; view answer, provenance, retrieval, validation.
- **Data Store Viewer**: inspect saved answers and indexed chunks.
- **Document Graph**: interactive graph (requires pyvis; handled by optional import).

## 6) Testing
```powershell
.\.venv\Scripts\Activate.ps1
pytest
```
Uses MiniLM to avoid paging issues; all tests should pass.

## 7) Common issues
- Paging file too small: stay on `all-MiniLM-L6-v2` (default) or increase paging file.
- RapidOCR missing paths: rerun Step 3 (RapidOCR Option A) to populate `%USERPROFILE%\.rapidocr`.
- If chroma warns about EmbeddingFunction.name(): safe to ignore for now.
