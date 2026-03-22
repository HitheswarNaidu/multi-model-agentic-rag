# ruff: noqa: E402

import importlib
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.utils.session import (
    get_pipeline,
    get_prewarm_status,
    reset_pipeline,
    start_pipeline_prewarm,
)
from rag.pipeline import DATA_DIR
from rag.utils.cache_manager import CacheManager

st.set_page_config(page_title="Admin | Multimodal Agentic RAG", layout="wide")
start_pipeline_prewarm()
pipeline = get_pipeline()
settings = pipeline.settings

st.title("Admin")
st.caption("Runtime controls, retrieval tuning, and maintenance actions.")

prewarm = get_prewarm_status()
st.markdown(f"**Warm-up status:** `{prewarm.get('state', 'pending')}`")

# Import context check lives here to keep Chat page clean.
try:
    importlib.import_module("rag.pipeline")
    importlib.import_module("rag.ingestion.parser")

    st.success("Runtime import context: OK")
except Exception as exc:  # pragma: no cover - only for UI diagnostics
    st.error(f"Runtime import context issue: {exc}")

st.subheader("Fast/Deep Behavior")
col1, col2 = st.columns(2)
with col1:
    vector_enabled = st.toggle(
        "Vector retrieval enabled (embeddings)",
        value=bool(settings.vector_enabled),
    )
    reranker_enabled = st.toggle("Reranker enabled", value=bool(settings.reranker_enabled))
with col2:
    hyde_enabled = st.toggle("HyDE enabled (deep mode)", value=bool(settings.hyde_enabled))
    deep_rewrite_enabled = st.toggle(
        "LLM deep rewrite enabled",
        value=bool(settings.deep_rewrite_enabled),
    )
    decomposition_enabled = st.toggle(
        "Question decomposition enabled",
        value=bool(settings.decomposition_enabled),
    )
    settings.ignore_test_demo_indexes = st.toggle(
        "Ignore demo/test indexes on startup",
        value=bool(settings.ignore_test_demo_indexes),
    )

pipeline.set_vector_enabled(vector_enabled)
pipeline.set_reranker_enabled(reranker_enabled)
pipeline.set_hyde_enabled(hyde_enabled)
pipeline.set_deep_rewrite_enabled(deep_rewrite_enabled)
pipeline.set_decomposition_enabled(decomposition_enabled)

if not pipeline.is_vector_available():
    st.info("Vector backend unavailable/disabled. Running BM25-only retrieval (no embeddings).")

bm25_weight, vector_weight = pipeline.get_retriever_weights()
new_bm25 = st.slider("BM25 weight", 0.0, 1.0, float(bm25_weight), 0.05)
new_vector = st.slider("Vector weight", 0.0, 1.0, float(vector_weight), 0.05)
if new_bm25 != bm25_weight or new_vector != vector_weight:
    pipeline.update_retriever_weights(new_bm25, new_vector)

st.subheader("Provider Status")
parse_status = "configured" if settings.llama_cloud_api_key else "missing key"
st.caption(f"Parser: LlamaParse ({parse_status})")
st.caption(f"Embeddings: NVIDIA ({settings.embedding_model})")
st.caption(f"LLM chain: {settings.llm_fallback_chain}")

st.subheader("Ingestion and Indexing Tuning")
tuning = pipeline.get_ingestion_tuning()
index_state = pipeline.get_index_registry_status()
st.caption(
    f"Swap mode: `{index_state.get('swap_mode')}` | "
    f"Active index: `{index_state.get('active', {}).get('index_id', 'n/a')}`"
)
integrity = index_state.get("integrity", {}) if isinstance(index_state, dict) else {}
if integrity:
    status_label = "suspicious" if integrity.get("suspicious") else "clean"
    st.caption(
        f"Active index integrity: `{status_label}` | "
        f"rows={int(integrity.get('rows', 0) or 0)}"
    )
    st.code(str(integrity.get("catalog_path", "n/a")))
    if integrity.get("suspicious"):
        st.warning("Active index contains demo/test-like artifacts and may pollute answers.")
        if st.button("Switch to latest clean index", type="primary"):
            switch_result = pipeline.switch_to_latest_clean_index()
            if switch_result.get("switched"):
                st.success(
                    f"Switched active index to {switch_result.get('active_index_id', 'n/a')}."
                )
                st.rerun()
            else:
                error = switch_result.get("error", {})
                st.error(
                    f"{error.get('code', 'SWITCH_FAILED')}: "
                    f"{error.get('message', switch_result.get('message', 'No switch occurred'))}"
                )
if index_state.get("staging"):
    st.info(f"Staging index in progress: {index_state['staging'].get('index_id')}")
recent_jobs = pipeline.list_ingestion_jobs()
if recent_jobs:
    latest_job = recent_jobs[0]
    st.caption(
        f"Latest job `{latest_job.get('job_id', 'n/a')}` status: "
        f"`{latest_job.get('status', 'unknown')}`"
    )
    latest_timing = latest_job.get("timing_ms", {})
    if isinstance(latest_timing, dict) and latest_timing:
        st.json({"latest_ingestion_timing_ms": latest_timing})

c3, c4 = st.columns(2)
with c3:
    parse_workers = st.number_input(
        "Parse workers",
        min_value=1,
        max_value=16,
        value=int(tuning["ingestion_parse_workers"]),
    )
    parse_queue = st.number_input(
        "Parse queue size",
        min_value=1,
        max_value=1024,
        value=int(tuning["ingestion_parse_queue_size"]),
    )
    embedding_batch_size = st.number_input(
        "Embedding batch size",
        min_value=1,
        max_value=256,
        value=int(tuning["embedding_batch_size"]),
    )
with c4:
    vector_upsert_batch_size = st.number_input(
        "Vector upsert batch size",
        min_value=1,
        max_value=2048,
        value=int(tuning["vector_upsert_batch_size"]),
    )
    bm25_commit_batch_size = st.number_input(
        "BM25 commit batch size",
        min_value=1,
        max_value=8192,
        value=int(tuning["bm25_commit_batch_size"]),
    )
    chunking_mode = st.selectbox(
        "Chunking mode",
        options=["window", "semantic_hybrid"],
        index=0 if str(tuning.get("chunking_mode", "window")) == "window" else 1,
        help="semantic_hybrid preserves semantic boundaries and can improve answer quality.",
    )
    index_swap_mode = st.selectbox(
        "Index swap mode",
        options=["atomic_swap"],
        index=0,
        disabled=True,
        help="Atomic swap is enforced for consistency.",
    )

pipeline.set_ingestion_tuning(
    ingestion_parse_workers=int(parse_workers),
    ingestion_parse_queue_size=int(parse_queue),
    embedding_batch_size=int(embedding_batch_size),
    vector_upsert_batch_size=int(vector_upsert_batch_size),
    bm25_commit_batch_size=int(bm25_commit_batch_size),
    chunking_mode=str(chunking_mode),
    index_swap_mode=index_swap_mode,
)

if st.button("Reset Tuning to Balanced Defaults"):
    pipeline.reset_ingestion_tuning_defaults()
    st.success("Balanced defaults restored. Reload this page to view applied values.")

st.subheader("Maintenance")
c1, c2 = st.columns(2)
with c1:
    if st.button("Clear Streamlit Cache"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Streamlit cache cleared.")

with c2:
    if st.button("Reload Pipeline Runtime"):
        reset_pipeline()
        start_pipeline_prewarm()
        st.success("Pipeline reset triggered.")

st.warning("Danger Zone")
if st.button("Hard Reset (Delete uploads + indices + outputs)"):
    cache = CacheManager(DATA_DIR)
    cache.clear_all()
    st.cache_data.clear()
    st.cache_resource.clear()
    st.success("Hard reset complete.")

with st.expander("Troubleshooting: stale Streamlit process", expanded=False):
    st.markdown("1. Stop the running Streamlit terminal process.")
    st.markdown("2. Run `run_app.bat` again.")
    st.markdown("3. Hard refresh browser (`Ctrl+Shift+R`).")
    st.markdown("4. If needed, remove `app/__pycache__` and relaunch.")
