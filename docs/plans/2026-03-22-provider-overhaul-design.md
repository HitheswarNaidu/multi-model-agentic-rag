# Provider Overhaul: LlamaParse + NVIDIA Embeddings + Groq/OpenRouter LLM

**Date:** 2026-03-22
**Status:** Approved

## Summary

Replace all parsing, embedding, and LLM providers. Enable all advanced RAG features by default.

| Layer | Current | New |
|-------|---------|-----|
| Parsing | PyMuPDF + Docling + RapidOCR | LlamaParse (cloud API) |
| Embeddings | SentenceTransformers (local, `all-mpnet-base-v2`) | NVIDIA API (`nvidia/llama-nemotron-embed-1b-v2`) |
| Vector store | ChromaDB | ChromaDB (unchanged) |
| LLM | Gemini 2.5 Flash | Groq primary + OpenRouter free fallback |
| Reranker | Local cross-encoder | Local cross-encoder (unchanged) |
| Advanced RAG | All OFF by default | All ON by default |

## 1. Parsing: LlamaParse Only

### Remove
- `pymupdf`, `docling`, `rapidocr`, `python-docx` dependencies
- All `DOCLING_OCR_*` env vars (6 fields)
- `PDF_PARSE_STRATEGY`, `PDF_TEXT_MIN_CHARS` config fields
- OCR validation logic in Admin page
- PyMuPDF/Docling fallback cascade in `parser.py`

### Add
- `llama-cloud-services` pip package (new SDK, replaces deprecated `llama-parse`)
- `LLAMA_CLOUD_API_KEY` env var

### Implementation

**`src/rag/ingestion/parser.py`** — full rewrite:

```python
from llama_cloud_services import LlamaParse

parser = LlamaParse(
    api_key=settings.llama_cloud_api_key,
    num_workers=settings.ingestion_parse_workers,
    language="en",
)
result = parser.parse(file_path)
markdown_docs = result.get_markdown_documents(split_by_page=True)
```

- Input: PDF, DOCX, images (130+ formats supported)
- Output: Clean Markdown per page — compatible with existing window chunker
- Async: `await parser.aparse()` for non-blocking ingestion
- Batch: `num_workers` for parallel file processing
- Page images: `result.get_image_documents()` available for future multimodal features

### Audit events
- `parser_strategy_selected` → always `"llamaparse"`
- `parser_fallback_used` → remove (single parser, no fallback)
- New: `llamaparse_credits_used` per job for cost tracking

## 2. Embeddings: NVIDIA API

### Remove
- `sentence-transformers` dependency
- Local embedding computation in `vector_store.py`

### Add
- `langchain-nvidia-ai-endpoints` pip package
- `NVIDIA_API_KEY` env var

### Implementation

**`src/rag/indexing/vector_store.py`** — replace embedding function:

```python
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

embedder = NVIDIAEmbeddings(
    model=settings.embedding_model,  # "nvidia/llama-nemotron-embed-1b-v2"
    truncate="END",
)
```

- Model: `nvidia/llama-nemotron-embed-1b-v2` (8192 token context, 2048 dims)
- ChromaDB stays as vector store, just with new embedding source
- `embed_query()` for queries, `embed_documents()` for chunks (input_type handled automatically)
- Tests: keep `hash-embedding` mock in conftest (no API calls in tests)

### Config changes
- `EMBEDDING_MODEL` default: `"nvidia/llama-nemotron-embed-1b-v2"` (was `"all-mpnet-base-v2"`)
- `VECTOR_ENABLED` default: `true` (was `false`)

## 3. LLM: Groq Primary + OpenRouter Fallback

### Remove
- `google-genai`, `langchain-google-genai` dependencies
- `GEMINI_API_KEY` env var
- Gemini-specific JSON extraction logic in `llm_client.py`

### Add
- `langchain-groq` pip package
- `langchain-openai` pip package (for OpenRouter via OpenAI-compatible API)
- `GROQ_API_KEY`, `OPENROUTER_API_KEY` env vars
- `LLM_FALLBACK_CHAIN` env var (user-configurable)

### Implementation

**`src/rag/generation/llm_client.py`** — rewrite with fallback chain:

```python
LLM_FALLBACK_CHAIN = "groq:llama-3.3-70b-versatile,groq:llama-3.1-8b-instant,openrouter:meta-llama/llama-3.3-70b-instruct:free,openrouter:openrouter/free"
```

For each `provider:model` in the chain:
- `groq:*` → `ChatGroq(model=model, api_key=settings.groq_api_key)`
- `openrouter:*` → `ChatOpenAI(model=model, base_url="https://openrouter.ai/api/v1", api_key=settings.openrouter_api_key)`

Fallback logic:
1. Try current provider:model
2. On 429 (rate limit) → next in chain
3. On auth/server error → raise immediately with `error.code`
4. All exhausted → raise `LLM_QUOTA_EXHAUSTED`

### Audit events
- `llm_provider` and `llm_model` fields on every `llm_finished` event
- `llm_fallback_used: true/false` when a non-primary model served the request

## 4. Advanced RAG: All ON by Default

### New defaults
```env
HYDE_ENABLED=true           # was false
DEEP_REWRITE_ENABLED=true   # was false
DECOMPOSITION_ENABLED=true  # was false
RERANKER_ENABLED=true       # was false
```

### Planner changes (`src/rag/agent/planner.py`)
- Default mode now includes all tools: `query_expander`, `query_rewriter`, `hyde_generator`, `decomposer`, `reranker`
- Planner still selects tools per intent — simple queries skip decomposition/HyDE
- Remove `FAST_PATH_ENABLED` flag (superseded)

### Mode semantics
- `mode=default` — full pipeline with all enabled features (new behavior)
- `mode=deep` — kept for backward compatibility, same as default now
- Admin toggles still control each feature individually

### Reranker
- Stays local: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- No new API dependency

## 5. Config Changes Summary

### `src/rag/config.py` field changes

**Add:**
- `llama_cloud_api_key: str`
- `nvidia_api_key: str`
- `groq_api_key: str`
- `openrouter_api_key: str`
- `llm_fallback_chain: str` (comma-separated `provider:model` pairs)

**Remove:**
- `gemini_api_key`
- `docling_ocr_force`, `docling_ocr_det_model_path`, `docling_ocr_cls_model_path`, `docling_ocr_rec_model_path`, `docling_ocr_rec_keys_path`, `docling_ocr_font_path`, `docling_ocr_auto`
- `pdf_parse_strategy`, `pdf_text_min_chars`
- `fast_path_enabled`

**Change defaults:**
- `embedding_model`: `"all-mpnet-base-v2"` → `"nvidia/llama-nemotron-embed-1b-v2"`
- `vector_enabled`: `false` → `true`
- `reranker_enabled`: `false` → `true`
- `hyde_enabled`: `false` → `true`
- `deep_rewrite_enabled`: `false` → `true`
- `decomposition_enabled`: `false` → `true`

## 6. Dependency Changes

### Add to `requirements.txt` / `pyproject.toml`
```
llama-cloud-services>=1.0
langchain-nvidia-ai-endpoints>=0.3.0
langchain-groq>=0.2.0
langchain-openai>=0.2.0
```

### Remove
```
google-genai
langchain-google-genai
sentence-transformers
docling
pymupdf
python-docx
pillow  # if only used for OCR; check other usages
```

## 7. Files to Change

| File | Change |
|------|--------|
| `src/rag/config.py` | New fields, remove OCR fields, change defaults |
| `src/rag/ingestion/parser.py` | Full rewrite → LlamaParse |
| `src/rag/ingestion/loader.py` | Update supported extensions (LlamaParse handles 130+) |
| `src/rag/indexing/vector_store.py` | NVIDIA embeddings via LangChain |
| `src/rag/generation/llm_client.py` | Groq/OpenRouter fallback chain |
| `src/rag/generation/prompts.py` | Update for Llama model prompt style if needed |
| `src/rag/agent/planner.py` | Default mode includes all deep tools |
| `src/rag/agent/hyde_generator.py` | Use new LLM client (was Gemini) |
| `src/rag/agent/query_rewriter.py` | Use new LLM client |
| `src/rag/agent/decomposer.py` | Use new LLM client |
| `src/rag/agent/summarizer.py` | Use new LLM client |
| `app/pages/4_🛠️_Admin.py` | Remove OCR validation, update provider display |
| `.env.example` | Full rewrite |
| `requirements.txt` | Dependency swap |
| `pyproject.toml` | Dependency swap |
| `tests/conftest.py` | Update mocks for new providers |
| `tests/test_ingestion/*` | Update parser tests |
| `tests/test_indexing/*` | Update embedding tests |
| `tests/test_generation/*` | Update LLM client tests |
| `CLAUDE.md` | Update policies |
| `AGENTS.md` | Update policies |
| `README.md` | Update setup/config docs |
| `CHANGELOG.md` | Document changes |

## 8. Migration Notes

- Existing indices (built with SentenceTransformers embeddings) are incompatible with NVIDIA embeddings. Users must re-index after upgrade.
- The index integrity check should detect dimension mismatch and prompt re-indexing.
- No backward compatibility with Gemini API key — clean break.
