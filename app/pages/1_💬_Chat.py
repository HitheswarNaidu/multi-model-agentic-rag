# ruff: noqa: E402

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
    append_chat_message,
    get_chat_history,
    get_expert_mode,
    get_ingestion_status,
    get_last_answer,
    get_pipeline,
    get_prewarm_status,
    get_selected_docs,
    get_selected_graph_chunks,
    get_selected_graph_filters,
    get_selected_graph_node,
    init_chat_state,
    set_last_answer,
    set_selected_docs,
    set_selected_graph_chunks,
    set_selected_graph_filters,
    set_selected_graph_node,
    start_pipeline_prewarm,
)

st.set_page_config(page_title="Chat | Multimodal Agentic RAG", layout="wide")
start_pipeline_prewarm()
init_chat_state()

pipeline = get_pipeline()

st.title("Multimodal Agentic RAG Chat")
st.caption("Upload files in-page, auto-index, then ask questions with citations.")

prewarm = get_prewarm_status()
prewarm_state = str(prewarm.get("state", "pending"))
if prewarm_state == "running":
    st.info("Runtime warm-up in progress.")
elif prewarm_state == "ready":
    duration = prewarm.get("result", {}).get("duration_ms", 0)
    st.success(f"Runtime warm-up ready ({duration} ms).")
elif prewarm_state == "failed":
    st.warning("Warm-up failed; runtime will initialize on demand.")

left, right = st.columns([2.0, 1.0], gap="large")

with left:
    st.subheader("Upload and Index")
    parse_preflight_ok = bool(pipeline.settings.llama_cloud_api_key)
    if not parse_preflight_ok:
        st.warning(
            "LLAMA_CLOUD_API_KEY is not set. File parsing will fail. "
            "Configure it in .env or the Admin page."
        )

    uploaded_files = st.file_uploader(
        "Drop files here",
        type=["pdf", "docx", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        help="Supported: PDF, DOCX, PNG, JPG, JPEG",
    )

    with st.expander("Indexing options", expanded=False):
        chunk_size = st.number_input(
            "Chunk size",
            min_value=100,
            max_value=5000,
            value=800,
            step=100,
        )
        chunk_overlap = st.number_input(
            "Chunk overlap",
            min_value=0,
            max_value=1000,
            value=80,
            step=10,
        )
        enable_hierarchy = st.toggle("Hierarchical chunking", value=True)
        chunking_mode = st.selectbox(
            "Chunking mode",
            options=["window", "semantic_hybrid"],
            index=0,
            help="semantic_hybrid improves semantic coherence with slight indexing overhead.",
        )

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button(
            "Upload + Start Indexing",
            type="primary",
            width="stretch",
            disabled=not parse_preflight_ok,
        ):
            result = pipeline.start_ingestion_job_for_uploads(
                uploaded_files=uploaded_files or [],
                chunk_size=int(chunk_size),
                chunk_overlap=int(chunk_overlap),
                enable_hierarchy=bool(enable_hierarchy),
                chunking_mode=str(chunking_mode),
            )
            st.session_state["latest_upload_result"] = result
            st.session_state["active_ingestion_job_id"] = result.get("job_id")
            if result.get("job_id"):
                status = str(result.get("status", "queued"))
                if status == "failed":
                    st.error(
                        f"Indexing job {result['job_id']} failed preflight: "
                        f"{result.get('error', 'Unknown error')}"
                    )
                    missing_paths = result.get("missing_paths") or []
                    if missing_paths:
                        st.code("\n".join(str(item) for item in missing_paths))
                elif status == "running":
                    st.info(f"Indexing started for job: {result['job_id']}")
                elif status == "completed":
                    st.success(f"Indexing already completed for job: {result['job_id']}")
                else:
                    st.success(f"Queued indexing job: {result['job_id']}")
                if result.get("saved_files"):
                    saved_count = len(result["saved_files"])
                    st.caption(f"Saved {saved_count} uploaded file(s) to data/uploads.")
            else:
                st.warning("No files uploaded.")
    if not parse_preflight_ok:
        st.caption("Set LLAMA_CLOUD_API_KEY in .env to enable document parsing.")

    with c2:
        if st.button("Refresh job status", width="stretch"):
            st.rerun()

    @st.fragment(run_every=2)
    def render_job_status() -> None:
        active_job_id = st.session_state.get("active_ingestion_job_id")
        if not active_job_id:
            return
        status = get_ingestion_status(active_job_id)
        if not status:
            st.warning(
                f"Job {active_job_id} was not found in the ingestion store. "
                "Try starting a new upload job."
            )
            return

        files_detected = int(status.get("files_detected", 0) or 0)
        processed = int(status.get("processed_files", 0) or 0)
        state = str(status.get("status", "unknown"))
        progress = (processed / files_detected) if files_detected else 0.0
        st.progress(min(max(progress, 0.0), 1.0), text=f"Job {active_job_id}: {state}")
        st.caption(
            f"Processed {processed}/{files_detected} | "
            f"Indexed {status.get('files_indexed', 0)} files | "
            f"Chunks {status.get('chunks_indexed', 0)}"
        )
        if state == "failed":
            st.error(status.get("error", "Indexing failed"))
            if status.get("missing_paths"):
                st.code("\n".join(str(item) for item in status["missing_paths"]))
            st.info("Open Admin page and run `Test OCR Setup` to validate Docling OCR paths.")
        elif state == "completed":
            st.success("Indexing completed. You can query the new index now.")
            st.session_state["docs_refresh_hint"] = True
        elif state in {"queued", "running"}:
            st.info("Indexing is in progress. This status block refreshes every 2 seconds.")

    render_job_status()

    ready = pipeline.has_ready_index()
    st.subheader("Chat")
    st.markdown(f"**Index status:** `{'READY' if ready else 'NOT_READY'}`")
    if st.session_state.get("docs_refresh_hint"):
        st.info("New index is ready. Click `Reload document list` to refresh filters.")

    docs = pipeline.list_documents()
    _, rc2 = st.columns([4, 1], gap="small")
    with rc2:
        if st.button("Reload document list", width="stretch"):
            st.session_state["docs_refresh_hint"] = False
            st.rerun()
    selected = st.multiselect(
        "Document filter",
        options=docs,
        default=get_selected_docs(),
        help="Leave empty to query across all indexed documents.",
    )
    set_selected_docs(selected)

    mode = st.radio(
        "Answer mode",
        options=["default", "deep"],
        horizontal=True,
        format_func=lambda x: "Fast" if x == "default" else "Deep",
    )
    show_internals = st.toggle(
        "Show internals",
        value=get_expert_mode(),
        help="Shows retrieval, validation, and execution traces for each answer.",
    )
    last_answer_payload = get_last_answer()
    quota_error = None
    if isinstance(last_answer_payload, dict):
        response_error = last_answer_payload.get("error", {})
        llm_error = (
            last_answer_payload.get("llm", {}).get("error", {})
            if isinstance(last_answer_payload.get("llm", {}), dict)
            else {}
        )
        error_code = str((response_error or llm_error).get("code", "") or "")
        if error_code == "LLM_QUOTA_EXHAUSTED":
            quota_error = str((response_error or llm_error).get("message", ""))
    if quota_error is not None:
        st.error(
            "LLM quota exhausted. Answers are temporarily unavailable. "
            "Wait for quota reset or use a higher-quota API key."
        )
        if quota_error:
            st.caption(quota_error[:500])
    graph_node = get_selected_graph_node()
    graph_filters = get_selected_graph_filters()
    graph_chunks = get_selected_graph_chunks()
    if graph_node or graph_filters or graph_chunks:
        st.info(
            "Graph scope active: "
            f"node={graph_node or 'n/a'} | "
            f"doc_ids={graph_filters.get('doc_ids', [])} | "
            f"chunk_ids={graph_chunks}"
        )
        g1, g2, g3 = st.columns([1, 1, 1], gap="small")
        with g1:
            if st.button("Ask: summarize selected graph context", width="stretch"):
                append_chat_message("user", "Summarize the selected graph context.")
                st.rerun()
        with g2:
            if st.button("Ask: key facts from selected node", width="stretch"):
                append_chat_message("user", "What are the key facts from the selected node?")
                st.rerun()
        with g3:
            if st.button("Clear graph scope", width="stretch"):
                set_selected_graph_node(None)
                set_selected_graph_filters({})
                set_selected_graph_chunks([])
                st.rerun()

    history = get_chat_history()
    for message in history:
        with st.chat_message(message.get("role", "assistant")):
            st.markdown(message.get("content", ""))
            payload = message.get("payload") if isinstance(message, dict) else None
            if payload and isinstance(payload, dict):
                response = payload.get("response", {})
                llm_payload = response.get("llm", {}) if isinstance(response, dict) else {}
                citations = (
                    llm_payload.get("provenance", []) if isinstance(llm_payload, dict) else []
                )
                if citations:
                    with st.expander("Citations", expanded=False):
                        retrieval = response.get("retrieval", [])
                        by_id = {
                            item.get("chunk_id"): item
                            for item in retrieval
                            if isinstance(item, dict) and item.get("chunk_id")
                        }
                        for cid in citations:
                            chunk = by_id.get(cid)
                            if chunk:
                                meta = (
                                    chunk.get("metadata", {})
                                    if isinstance(chunk.get("metadata"), dict)
                                    else {}
                                )
                                st.markdown(
                                    f"`{cid}` | "
                                    f"{meta.get('doc_id', chunk.get('doc_id', 'unknown'))} | "
                                    f"{meta.get('chunk_type', chunk.get('chunk_type', 'unknown'))}"
                                )
                                st.caption((chunk.get("content", "") or "")[:400])
                            else:
                                st.markdown(f"`{cid}`")
                timing = response.get("timing_ms", {})
                quality = response.get("quality", {})
                if timing:
                    st.caption(
                        f"latency: retrieval={timing.get('retrieval_ms', 0)} ms | "
                        f"llm={timing.get('llm_ms', 0)} ms | total={timing.get('total_ms', 0)} ms"
                    )
                if quality:
                    st.caption(
                        f"quality: valid={quality.get('validation_valid')} | "
                        f"citation_hit={quality.get('citation_hit')} | "
                        f"retrieval_count={quality.get('retrieval_count', 0)}"
                    )
                if show_internals:
                    with st.expander("Internals", expanded=False):
                        st.json(
                            {
                                "request_id": response.get("request_id"),
                                "timing_ms": response.get("timing_ms", {}),
                                "quality": response.get("quality", {}),
                                "validation": response.get("validation", {}),
                                "feature_flags": response.get("feature_flags", {}),
                            }
                        )

    prompt = st.chat_input("Ask a question about your uploaded documents")
    if prompt:
        append_chat_message("user", prompt)
        if not ready:
            append_chat_message(
                "assistant",
                "Index is not ready yet. Upload documents and wait for indexing to complete.",
            )
            st.rerun()

        filters = {}
        if selected:
            filters["doc_ids"] = selected
        if graph_filters:
            graph_doc_ids = graph_filters.get("doc_ids")
            if isinstance(graph_doc_ids, list) and graph_doc_ids:
                filters["doc_ids"] = sorted(
                    set([str(item) for item in filters.get("doc_ids", [])] + graph_doc_ids)
                )
        if graph_chunks:
            filters["chunk_ids"] = [str(item) for item in graph_chunks]
        if not filters:
            filters = None

        response = pipeline.query_fast(prompt, filters=filters, mode=mode)
        llm_payload = response.get("llm", {})
        answer = llm_payload.get("answer", "(no answer)")
        append_chat_message(
            "assistant",
            answer,
            payload={
                "response": response,
            },
        )
        set_last_answer(response)
        st.rerun()

with right:
    st.subheader("Quick Diagnostics")
    last_answer = get_last_answer()
    if isinstance(last_answer, dict):
        st.markdown(f"**Last request:** `{last_answer.get('request_id', 'n/a')}`")
        timing = last_answer.get("timing_ms", {})
        if timing:
            st.metric("Total latency (ms)", int(timing.get("total_ms", 0) or 0))
        quality = last_answer.get("quality", {})
        if quality:
            st.metric("Citation hit", str(quality.get("citation_hit", False)))
            st.metric("Validation valid", str(quality.get("validation_valid", False)))
    else:
        st.info("No answers yet.")

    chunks = pipeline.saved_chunks()
    doc_count = len({c.get("doc_id") for c in chunks if isinstance(c, dict) and c.get("doc_id")})
    st.metric("Indexed documents", doc_count)
    st.metric("Indexed chunks", len(chunks))

    st.markdown("**Navigation**")
    st.page_link("pages/2_🗄️_Data_Store.py", label="Data Store", icon="🗄️")
    st.page_link("pages/3_🕸️_Knowledge_Graph.py", label="Knowledge Graph", icon="🕸️")
    st.page_link("pages/4_🛠️_Admin.py", label="Admin", icon="🛠️")
