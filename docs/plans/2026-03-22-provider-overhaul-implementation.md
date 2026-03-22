# Provider Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace all parsing (LlamaParse), embedding (NVIDIA), and LLM (Groq/OpenRouter) providers; enable all advanced RAG features by default.

**Architecture:** Config-first approach — update Settings and dependencies first, then rewrite each layer bottom-up (parser → embeddings → LLM → planner → Admin UI → docs). Each task is independently testable.

**Tech Stack:** `llama-cloud-services`, `langchain-nvidia-ai-endpoints`, `langchain-groq`, `langchain-openai`, `chromadb`, `whoosh`

---

### Task 1: Update Dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `pyproject.toml`
- Modify: `.env.example`

**Step 1: Replace requirements.txt**

Remove: docling, rapidocr-onnxruntime, pymupdf, python-docx, pillow, sentence-transformers, langchain-google-genai, google-genai.
Add: llama-cloud-services>=1.0, langchain-nvidia-ai-endpoints>=0.3.0, langchain-groq>=0.2.0, langchain-openai>=0.2.0.

**Step 2: Replace pyproject.toml dependencies**

Same additions/removals in the `dependencies` array.

**Step 3: Replace .env.example**

New vars: LLAMA_CLOUD_API_KEY, NVIDIA_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, LLM_FALLBACK_CHAIN.
Remove: GEMINI_API_KEY, all DOCLING_OCR_* vars, PDF_PARSE_STRATEGY, PDF_TEXT_MIN_CHARS, FAST_PATH_ENABLED.
Change defaults: VECTOR_ENABLED=true, HYDE_ENABLED=true, DEEP_REWRITE_ENABLED=true, DECOMPOSITION_ENABLED=true, RERANKER_ENABLED=true.

**Step 4: Commit**

```bash
git add requirements.txt pyproject.toml .env.example
git commit -m "chore: swap dependencies to LlamaParse, NVIDIA embeddings, Groq/OpenRouter LLM"
```

---

### Task 2: Rewrite Config (Settings)

**Files:**
- Modify: `src/rag/config.py`
- Create: `tests/test_config.py`

**Step 1: Write failing test**

```python
from rag.config import Settings

def test_new_api_key_fields():
    s = Settings(llama_cloud_api_key="llx-test", nvidia_api_key="nvapi-test",
                 groq_api_key="gsk_test", openrouter_api_key="sk-or-test")
    assert s.llama_cloud_api_key == "llx-test"
    assert s.nvidia_api_key == "nvapi-test"

def test_new_defaults():
    s = Settings()
    assert s.vector_enabled is True
    assert s.hyde_enabled is True
    assert s.deep_rewrite_enabled is True
    assert s.decomposition_enabled is True
    assert s.reranker_enabled is True
    assert s.embedding_model == "nvidia/llama-nemotron-embed-1b-v2"

def test_llm_fallback_chain_default():
    s = Settings()
    assert "groq:" in s.llm_fallback_chain

def test_removed_fields_absent():
    s = Settings()
    assert not hasattr(s, "gemini_api_key")
    assert not hasattr(s, "docling_ocr_force")
    assert not hasattr(s, "fast_path_enabled")
```

**Step 2: Run to verify failure**

Run: `pytest tests/test_config.py -v`

**Step 3: Rewrite src/rag/config.py**

Remove fields: gemini_api_key, fast_path_enabled, docling_ocr_force, docling_ocr_det_model_path, docling_ocr_cls_model_path, docling_ocr_rec_model_path, docling_ocr_rec_keys_path, docling_ocr_font_path, docling_ocr_auto, pdf_parse_strategy, pdf_text_min_chars.

Add fields: llama_cloud_api_key (str, ""), nvidia_api_key (str, ""), groq_api_key (str, ""), openrouter_api_key (str, ""), llm_fallback_chain (str, default chain).

Change defaults: embedding_model="nvidia/llama-nemotron-embed-1b-v2", vector_enabled=True, reranker_enabled=True, hyde_enabled=True, deep_rewrite_enabled=True, decomposition_enabled=True.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_config.py -v`

**Step 5: Commit**

```bash
git add src/rag/config.py tests/test_config.py
git commit -m "feat: rewrite Settings for new providers"
```

---

### Task 3: Rewrite Parser (LlamaParse)

**Files:**
- Modify: `src/rag/ingestion/parser.py` (full rewrite)
- Modify: `src/rag/ingestion/loader.py`
- Create: `tests/test_ingestion/test_parser_llamaparse.py`

**Step 1: Write failing test**

```python
from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest
from rag.config import Settings
from rag.ingestion.parser import Block, DocumentParseResult, LlamaParseError, parse_document

def _mock_result(pages_md):
    docs = []
    for md in pages_md:
        doc = MagicMock()
        doc.text = md
        docs.append(doc)
    result = MagicMock()
    result.get_markdown_documents.return_value = docs
    return result

@patch("rag.ingestion.parser.LlamaParse")
def test_parse_pdf(mock_cls, tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    mock_cls.return_value.parse.return_value = _mock_result(["# Page 1\nContent"])
    settings = Settings(llama_cloud_api_key="llx-test")
    result = parse_document(pdf, settings=settings)
    assert len(result.blocks) == 1
    assert result.blocks[0].page == 1
    assert result.parse_meta["parser_used"] == "llamaparse"

def test_missing_api_key(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    settings = Settings(llama_cloud_api_key="")
    with pytest.raises(LlamaParseError, match="LLAMA_CLOUD_API_KEY"):
        parse_document(pdf, settings=settings)

def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        parse_document(Path("/nonexistent.pdf"))
```

**Step 2: Run to verify failure**

Run: `pytest tests/test_ingestion/test_parser_llamaparse.py -v`

**Step 3: Rewrite src/rag/ingestion/parser.py**

Full rewrite. Keep Block and DocumentParseResult dataclasses. Replace all parsing functions with single LlamaParse integration. New error class: LlamaParseError. Remove: OCRConfigurationError, DoclingParseError, PDFParseError, all _parse_with_* functions, validate_docling_ocr_assets, _build_docling_converter.

The new parse_document function: validates path exists, checks LLAMA_CLOUD_API_KEY is set, calls LlamaParse.parse(), extracts markdown docs per page, converts to Block list.

**Step 4: Update loader.py**

Expand SUPPORTED_EXTS to include all LlamaParse-supported formats: .pdf, .docx, .doc, .pptx, .ppt, .xlsx, .xls, .csv, .tsv, .rtf, .txt, .epub, .png, .jpg, .jpeg, .gif, .bmp, .tiff, .webp, .html, .htm, .xml.

**Step 5: Run test to verify pass**

Run: `pytest tests/test_ingestion/test_parser_llamaparse.py -v`

**Step 6: Commit**

```bash
git add src/rag/ingestion/parser.py src/rag/ingestion/loader.py tests/test_ingestion/test_parser_llamaparse.py
git commit -m "feat: replace PyMuPDF/Docling/RapidOCR with LlamaParse"
```

---

### Task 4: Rewrite Vector Store Embeddings (NVIDIA)

**Files:**
- Modify: `src/rag/indexing/vector_store.py`
- Create: `tests/test_indexing/test_nvidia_embeddings.py`

**Step 1: Write failing test**

```python
from unittest.mock import MagicMock, patch
from rag.indexing.vector_store import NVIDIAEmbeddingFunction, HashEmbeddingFunction

def test_hash_embedding_unchanged():
    fn = HashEmbeddingFunction(dimension=64)
    result = fn(["hello"])
    assert len(result) == 1
    assert len(result[0]) == 64

@patch("rag.indexing.vector_store.NVIDIAEmbeddings")
def test_nvidia_embedding(mock_cls):
    mock_cls.return_value.embed_documents.return_value = [[0.1] * 2048]
    fn = NVIDIAEmbeddingFunction(model_name="nvidia/llama-nemotron-embed-1b-v2", api_key="nvapi-test")
    result = fn(["hello"])
    assert len(result) == 1
```

**Step 2: Run to verify failure**

Run: `pytest tests/test_indexing/test_nvidia_embeddings.py -v`

**Step 3: Rewrite src/rag/indexing/vector_store.py**

Remove SentenceTransformerEmbeddingFunction class entirely. Add NVIDIAEmbeddingFunction class that wraps langchain_nvidia_ai_endpoints.NVIDIAEmbeddings (lazy import). Keep HashEmbeddingFunction unchanged. Update VectorStore constructor to use NVIDIAEmbeddingFunction as default (instead of SentenceTransformer), add nvidia_api_key parameter. Keep all existing VectorStore methods, NoOpVectorStore, search logic identical.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_indexing/test_nvidia_embeddings.py -v`

**Step 5: Commit**

```bash
git add src/rag/indexing/vector_store.py tests/test_indexing/test_nvidia_embeddings.py
git commit -m "feat: replace SentenceTransformers with NVIDIA embedding API"
```

---

### Task 5: Rewrite LLM Client (Groq/OpenRouter Fallback)

**Files:**
- Modify: `src/rag/generation/llm_client.py` (full rewrite)
- Create: `tests/test_generation/test_llm_fallback.py`

**Step 1: Write failing test**

```python
from unittest.mock import patch
import pytest
from rag.generation.llm_client import LLMClient, LLMQuotaExhaustedError, MockLLMClient, RateLimitError

def test_mock_client():
    mock = MockLLMClient(payload={"answer": "test", "provenance": []})
    assert mock.generate([], "q")["answer"] == "test"

def test_parse_chain():
    client = LLMClient.__new__(LLMClient)
    chain = client._parse_chain("groq:model-a,openrouter:model-b")
    assert chain == [("groq", "model-a"), ("openrouter", "model-b")]

@patch("rag.generation.llm_client.LLMClient._call_provider")
def test_fallback_on_rate_limit(mock_call):
    mock_call.side_effect = [RateLimitError("429"), {"answer": "ok", "provenance": []}]
    client = LLMClient(groq_api_key="k", openrouter_api_key="k", fallback_chain="groq:a,openrouter:b")
    result = client.generate([], "q")
    assert result["answer"] == "ok"
    assert result["_llm_provider"] == "openrouter"

@patch("rag.generation.llm_client.LLMClient._call_provider")
def test_all_exhausted(mock_call):
    mock_call.side_effect = RateLimitError("429")
    client = LLMClient(groq_api_key="k", openrouter_api_key="k", fallback_chain="groq:a,openrouter:b")
    with pytest.raises(LLMQuotaExhaustedError):
        client.generate([], "q")
```

**Step 2: Run to verify failure**

Run: `pytest tests/test_generation/test_llm_fallback.py -v`

**Step 3: Rewrite src/rag/generation/llm_client.py**

Remove google.genai import. New classes: RateLimitError, LLMQuotaExhaustedError. LLMClient constructor takes groq_api_key, openrouter_api_key, fallback_chain. Parses chain into list of (provider, model) tuples. generate() iterates chain, calling _call_provider for each. _call_provider builds ChatGroq or ChatOpenAI, invokes, parses JSON response. On 429/rate errors, raises RateLimitError which generate() catches to try next. If all exhausted, raises LLMQuotaExhaustedError. Keeps _extract_json_payload and response normalization logic. MockLLMClient unchanged.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_generation/test_llm_fallback.py -v`

**Step 5: Commit**

```bash
git add src/rag/generation/llm_client.py tests/test_generation/test_llm_fallback.py
git commit -m "feat: replace Gemini with Groq/OpenRouter fallback chain"
```

---

### Task 6: Update Pipeline Wiring

**Files:**
- Modify: `src/rag/pipeline.py`
- Modify: `tests/conftest.py`

**Step 1: Update conftest.py**

Replace DOCLING_OCR_FORCE env with LLAMA_CLOUD_API_KEY="". Add monkeypatches for GROQ_API_KEY="", OPENROUTER_API_KEY="", NVIDIA_API_KEY="", VECTOR_ENABLED="false".

**Step 2: Update pipeline.py imports**

Replace `from rag.ingestion.parser import (DoclingParseError, OCRConfigurationError, parse_document, validate_docling_ocr_assets)` with `from rag.ingestion.parser import LlamaParseError, parse_document`.

**Step 3: Update _ensure_runtime_initialized**

Replace `llm_key = self.settings.gemini_api_key` block with Groq/OpenRouter initialization. Pass nvidia_api_key to _build_vector_store.

**Step 4: Update _build_vector_store**

Add nvidia_api_key=self.settings.nvidia_api_key to VectorStore constructor call.

**Step 5: Update _ingest_files**

Remove OCR validation block (the `if self.settings.docling_ocr_force` block). Replace DoclingParseError catches with LlamaParseError. Update audit event strategy references from self.settings.pdf_parse_strategy to "llamaparse".

**Step 6: Remove set_fast_path_enabled and related methods**

Remove any methods that reference fast_path_enabled, docling_ocr_force, pdf_parse_strategy, pdf_text_min_chars.

**Step 7: Run tests**

Run: `pytest -q`

**Step 8: Commit**

```bash
git add src/rag/pipeline.py tests/conftest.py
git commit -m "feat: wire new providers into Pipeline"
```

---

### Task 7: Update Planner (All Advanced Features ON)

**Files:**
- Modify: `src/rag/agent/planner.py`

**Step 1: Remove mode gating in make_plan**

Delete lines 80-91 (the `if mode != "deep"` block that filters steps to core tools only). All steps now available regardless of mode.

**Step 2: Remove mode gating in execute**

Change `if mode == "deep" and self.enable_decomposition` to `if self.enable_decomposition`.
Change `if mode == "deep" and self.expander` to `if self.expander`.
Change `if mode == "deep" and self.enable_hyde` to `if self.enable_hyde`.

**Step 3: Run tests**

Run: `pytest tests/test_agent/ -v`

**Step 4: Commit**

```bash
git add src/rag/agent/planner.py
git commit -m "feat: remove mode gating, all advanced RAG features available by default"
```

---

### Task 8: Update Admin Page

**Files:**
- Modify: `app/pages/4_🛠️_Admin.py`

**Step 1: Remove OCR imports and section**

Remove `from rag.ingestion.parser import OCRConfigurationError, validate_docling_ocr_assets` import. Remove entire "Docling OCR (Strict)" section (lines 212-268). Remove fast_path_enabled toggle. Remove pdf_parse_strategy selectbox and pdf_text_min_chars input. Remove those fields from set_ingestion_tuning call.

**Step 2: Add provider status**

Add after "Fast/Deep Behavior" section:
```python
st.subheader("Provider Status")
st.caption(f"Parser: LlamaParse ({'configured' if settings.llama_cloud_api_key else 'missing key'})")
st.caption(f"Embeddings: NVIDIA ({settings.embedding_model})")
st.caption(f"LLM chain: {settings.llm_fallback_chain}")
```

**Step 3: Commit**

```bash
git add "app/pages/4_🛠️_Admin.py"
git commit -m "feat: update Admin page for new providers"
```

---

### Task 9: Fix All Remaining Tests

**Files:**
- Modify: various test files

**Step 1: Find broken references**

Search for: OCRConfigurationError, DoclingParseError, validate_docling_ocr_assets, gemini_api_key, docling_ocr_force, fast_path_enabled, pdf_parse_strategy, SentenceTransformerEmbeddingFunction, _parse_with_pymupdf, _parse_with_docling, _parse_docx, _parse_image across all test files.

**Step 2: Fix each broken test**

- Replace old error classes with LlamaParseError
- Replace old config field references with new ones
- Remove tests for deleted functionality (OCR validation tests, PyMuPDF/Docling parser tests)
- Update mock patterns for new LLMClient constructor signature

**Step 3: Run full suite**

Run: `pytest -q`

**Step 4: Run linter**

Run: `ruff check src app tests`

**Step 5: Commit**

```bash
git add -A
git commit -m "fix: update all tests for new provider stack"
```

---

### Task 10: Update Documentation

**Files:**
- Modify: `CLAUDE.md`, `AGENTS.md`, `README.md`, `CHANGELOG.md`

**Step 1: Update CLAUDE.md**

Remove OCR Policy section. Remove Vector Policy section (vector is now default-on). Update Architecture section for new providers. Remove PDF_PARSE_STRATEGY references. Update Retrieval/Reasoning Defaults to reflect all-ON advanced features.

**Step 2: Update AGENTS.md**

Remove OCR references. Update provider references. Update Product Direction.

**Step 3: Update README.md**

Replace env var setup section. Replace architecture overview.

**Step 4: Add CHANGELOG.md entry**

Document all breaking changes, additions, and removals.

**Step 5: Commit**

```bash
git add CLAUDE.md AGENTS.md README.md CHANGELOG.md
git commit -m "docs: update all documentation for provider overhaul"
```

---

### Task 11: Final Verification

**Step 1: Run linter**

Run: `ruff check src app tests`
Expected: 0 errors

**Step 2: Run full test suite**

Run: `pytest -q`
Expected: All pass

**Step 3: Grep for stale references**

Run: `grep -r "gemini_api_key\|docling_ocr_force\|SentenceTransformerEmbeddingFunction\|fast_path_enabled\|from google import genai" src/ app/`
Expected: No results

**Step 4: Commit if needed**

```bash
git add -A
git commit -m "chore: final cleanup after provider overhaul"
```
