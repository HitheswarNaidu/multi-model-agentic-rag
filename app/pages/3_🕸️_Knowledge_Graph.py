# ruff: noqa: E402

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.components.graph_viewer import get_node_detail, render_graph
from app.utils.session import (
    get_expert_mode,
    get_pipeline,
    get_selected_graph_node,
    set_expert_mode,
    set_selected_graph_chunks,
    set_selected_graph_filters,
    set_selected_graph_node,
    start_pipeline_prewarm,
)
from rag.chunking.metadata import ChunkMetadata, DocumentChunk
from rag.utils.audit_logger import new_request_id
from rag.visualization.graph_builder import build_chunk_graph

st.set_page_config(page_title="Knowledge Graph | Multimodal Agentic RAG", layout="wide")
start_pipeline_prewarm()
pipeline = get_pipeline()

st.title("Knowledge Graph")
st.caption("Interactive investigation workspace for document and chunk relationships.")

expert_mode = st.toggle("Expert mode", value=get_expert_mode())
set_expert_mode(expert_mode)

chunks = pipeline.saved_chunks()
if not chunks:
    st.info("No graph data yet. Upload and index documents from Chat first.")
    st.stop()


@st.cache_data(show_spinner=False)
def _build_graph_cached(rows_json: str) -> dict:
    parsed_rows = json.loads(rows_json)
    node_chunks: list[DocumentChunk] = []
    for row in parsed_rows:
        if not isinstance(row, dict) or not row.get("chunk_id"):
            continue
        metadata = ChunkMetadata(
            doc_id=str(row.get("doc_id", "")),
            doc_type=str(row.get("doc_type", "")),
            page=int(row.get("page", 0) or 0),
            section=str(row.get("section", "") or ""),
            chunk_id=str(row.get("chunk_id", "")),
            chunk_type=str(row.get("chunk_type", "paragraph")),
            table_id=None,
            confidence=1.0,
            source_path=str(row.get("source_path", "") or ""),
            source_hash=str(row.get("source_hash", "") or ""),
            ingest_timestamp_utc=str(row.get("ingest_timestamp_utc", "") or ""),
            is_table=bool(row.get("is_table", False)),
            is_image=bool(row.get("is_image", False)),
            semantic_group_id=str(row.get("semantic_group_id", "") or "") or None,
            boundary_reason=str(row.get("boundary_reason", "") or "") or None,
        )
        node_chunks.append(DocumentChunk(metadata=metadata, content=str(row.get("content", ""))))
    graph = build_chunk_graph(
        node_chunks,
        include_doc_nodes=True,
        include_edge_types=True,
        include_semantic_edges=True,
        include_adjacency_edges=True,
        include_doc_similarity_edges=True,
    )
    return {
        "graph": graph,
        "doc_options": sorted(
            {meta.metadata.doc_id for meta in node_chunks if meta.metadata.doc_id}
        ),
        "chunk_options": sorted(
            {
                meta.metadata.chunk_type
                for meta in node_chunks
                if meta.metadata.chunk_type and meta.metadata.chunk_type != "doc"
            }
        ),
    }


graph_payload = _build_graph_cached(json.dumps(chunks, ensure_ascii=True))
graph = graph_payload["graph"]
doc_options = graph_payload["doc_options"]
edge_types_all = sorted(
    {
        str(attrs.get("edge_type", "edge"))
        for _src, _dst, attrs in graph.edges(data=True)
        if str(attrs.get("edge_type", "edge"))
    }
)

if "kg_doc_filter" not in st.session_state:
    st.session_state["kg_doc_filter"] = "All"
if "kg_selected_node" not in st.session_state:
    st.session_state["kg_selected_node"] = get_selected_graph_node() or ""

controls = st.columns([1, 1, 1], gap="small")
with controls[0]:
    layout_mode = st.radio("View", options=["3D", "2D"], horizontal=True, index=0)
with controls[1]:
    max_nodes = st.slider("Node cap", min_value=50, max_value=800, value=300, step=25)
with controls[2]:
    doc_choices = ["All"] + doc_options
    doc_filter = st.selectbox(
        "Document",
        options=doc_choices,
        index=doc_choices.index(st.session_state["kg_doc_filter"])
        if st.session_state["kg_doc_filter"] in doc_choices
        else 0,
    )
    st.session_state["kg_doc_filter"] = doc_filter

if doc_filter != "All":
    filtered_ids = {f"doc:{doc_filter}"} | {
        str(node)
        for node, attrs in graph.nodes(data=True)
        if str(attrs.get("doc_id", "")) == doc_filter
    }
    graph = graph.subgraph(filtered_ids).copy()

candidate_nodes = sorted([str(node) for node in graph.nodes()])
selected_node = st.selectbox(
    "Node",
    options=[""] + candidate_nodes,
    index=([""] + candidate_nodes).index(st.session_state["kg_selected_node"])
    if st.session_state["kg_selected_node"] in candidate_nodes
    else 0,
    help="Pick a node to inspect what it contains and why it is connected.",
)
st.session_state["kg_selected_node"] = selected_node

pipeline.audit_logger.log_event(
    "kg_view_loaded",
    mode="runtime",
    quality={
        "layout_mode": layout_mode,
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "doc_filter": doc_filter,
    },
)
pipeline.audit_logger.log_event(
    "kg_filter_applied",
    mode="runtime",
    quality={
        "doc_filter": doc_filter,
        "edge_types": edge_types_all,
        "search": "",
        "focus_mode": False,
        "depth": 0,
    },
)

c1, c2 = st.columns([2, 1], gap="large")
with c1:
    rendered_graph, graph_stats = render_graph(
        graph=graph,
        mode="3D" if layout_mode == "3D" else "2D force",
        selected_node=selected_node or None,
        depth=0,
        focus_mode=False,
        pinned_nodes=[],
        edge_types=edge_types_all,
        search="",
        max_nodes=max_nodes,
        show_labels=bool(expert_mode and layout_mode == "2D"),
    )
    if graph_stats.get("node_cap_hit"):
        st.warning(
            f"Node cap reached ({max_nodes}). Narrow filters/search or increase cap for more nodes."
        )
    if selected_node:
        pipeline.audit_logger.log_event(
            "kg_node_selected",
            mode="runtime",
            quality={"selected_node": selected_node, "depth": 0},
        )

with c2:
    st.subheader("Graph Stats")
    st.metric("Nodes", rendered_graph.number_of_nodes())
    st.metric("Edges", rendered_graph.number_of_edges())
    st.metric("Matched nodes", int(graph_stats.get("match_count", 0)))

    detail = get_node_detail(rendered_graph, selected_node or None)
    st.subheader("Node Details")
    if detail:
        st.markdown(f"**ID:** `{detail.get('node_id')}`")
        st.caption(
            f"type={detail.get('node_type')} | doc={detail.get('doc_id')} | "
            f"page={detail.get('page')} | chunk_type={detail.get('chunk_type')}"
        )
        if detail.get("section"):
            st.caption(f"section: {detail.get('section')}")
        if detail.get("content_preview"):
            st.text_area(
                "Chunk preview",
                value=str(detail.get("content_preview", "")),
                height=120,
                disabled=True,
            )
        st.caption(f"Connected neighbors: {detail.get('neighbor_count', 0)}")
        related = detail.get("related", [])
        if related:
            st.markdown("**Why related**")
            for rel in related[:10]:
                st.caption(
                    f"- `{rel.get('neighbor')}` via `{rel.get('edge_type')}`: "
                    f"{rel.get('reason') or 'related in graph'}"
                )

        a1, a2 = st.columns(2, gap="small")
        with a1:
            if st.button("Ask Chat about this node", width="stretch"):
                doc_id = str(detail.get("doc_id", "") or "")
                chunk_id = str(detail.get("chunk_id", "") or "")
                scoped_filters = {"doc_ids": [doc_id]} if doc_id else {}
                scoped_chunks = [chunk_id] if chunk_id else []
                set_selected_graph_node(str(detail.get("node_id")))
                set_selected_graph_filters(scoped_filters)
                set_selected_graph_chunks(scoped_chunks)
                pipeline.audit_logger.log_event(
                    "kg_chat_bridge_invoked",
                    request_id=new_request_id(),
                    mode="runtime",
                    quality={"node_id": detail.get("node_id"), "filters": scoped_filters},
                )
                st.switch_page("pages/1_💬_Chat.py")
        with a2:
            if st.button("Filter graph to this doc", width="stretch"):
                doc_value = str(detail.get("doc_id", "") or "")
                if doc_value:
                    st.session_state["kg_doc_filter"] = doc_value
                    pipeline.audit_logger.log_event(
                        "kg_filter_applied",
                        mode="runtime",
                        quality={"doc_filter": doc_value, "source": "node_action"},
                    )
                st.rerun()
    else:
        st.info("Select a node to inspect details and actions.")

    if expert_mode:
        st.subheader("Sample Nodes")
        for node, attrs in list(rendered_graph.nodes(data=True))[:15]:
            st.code(f"{node}: {attrs}")
