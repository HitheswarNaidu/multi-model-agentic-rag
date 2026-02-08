from __future__ import annotations

import threading
from functools import lru_cache
from typing import Any

import streamlit as st

from rag.pipeline import Pipeline, load_pipeline


@lru_cache(maxsize=1)
def get_pipeline() -> Pipeline:
    return load_pipeline()


_PREWARM_LOCK = threading.Lock()
_PREWARM_THREAD: threading.Thread | None = None
_PREWARM_STATUS: dict[str, object] = {"state": "pending", "result": None}


def _prewarm_worker() -> None:
    try:
        result = get_pipeline().warm_up()
        _PREWARM_STATUS["state"] = "ready" if result.get("status") == "ready" else "failed"
        _PREWARM_STATUS["result"] = result
    except Exception as exc:
        _PREWARM_STATUS["state"] = "failed"
        _PREWARM_STATUS["result"] = {"status": "failed", "error": str(exc)}


def start_pipeline_prewarm() -> None:
    global _PREWARM_THREAD
    with _PREWARM_LOCK:
        if _PREWARM_STATUS["state"] in {"running", "ready"}:
            return
        _PREWARM_STATUS["state"] = "running"
        _PREWARM_THREAD = threading.Thread(target=_prewarm_worker, daemon=True)
        _PREWARM_THREAD.start()


def get_prewarm_status() -> dict[str, object]:
    return dict(_PREWARM_STATUS)


def reset_pipeline() -> None:
    global _PREWARM_THREAD
    get_pipeline.cache_clear()
    with _PREWARM_LOCK:
        _PREWARM_THREAD = None
        _PREWARM_STATUS["state"] = "pending"
        _PREWARM_STATUS["result"] = None


def get_state(name: str, default: Any = None) -> Any:
    if name not in st.session_state:
        st.session_state[name] = default
    return st.session_state[name]


def set_state(name: str, value: Any) -> None:
    st.session_state[name] = value


def get_ingestion_status(job_id: str) -> dict | None:
    return get_pipeline().get_ingestion_job(job_id)


def index_ready() -> bool:
    return get_pipeline().has_ready_index()


def init_chat_state() -> None:
    defaults: dict[str, Any] = {
        "chat_history": [],
        "last_answer": None,
        "selected_docs": [],
        "expert_mode": False,
        "active_ingestion_job_id": None,
        "latest_upload_result": None,
        "selected_graph_node": None,
        "selected_graph_filters": {},
        "selected_graph_chunks": [],
        "pinned_graph_nodes": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_chat_history() -> list[dict[str, Any]]:
    init_chat_state()
    return st.session_state["chat_history"]


def clear_chat_history() -> None:
    st.session_state["chat_history"] = []


def append_chat_message(role: str, content: str, payload: dict[str, Any] | None = None) -> None:
    init_chat_state()
    st.session_state["chat_history"].append(
        {
            "role": role,
            "content": content,
            "payload": payload or {},
        }
    )


def set_last_answer(answer_payload: dict[str, Any] | None) -> None:
    st.session_state["last_answer"] = answer_payload


def get_last_answer() -> dict[str, Any] | None:
    init_chat_state()
    value = st.session_state.get("last_answer")
    if isinstance(value, dict):
        return value
    return None


def set_selected_docs(doc_ids: list[str]) -> None:
    st.session_state["selected_docs"] = doc_ids


def get_selected_docs() -> list[str]:
    init_chat_state()
    current = st.session_state.get("selected_docs", [])
    if isinstance(current, list):
        return [str(item) for item in current]
    return []


def set_expert_mode(enabled: bool) -> None:
    st.session_state["expert_mode"] = bool(enabled)


def get_expert_mode() -> bool:
    init_chat_state()
    return bool(st.session_state.get("expert_mode", False))


def set_selected_graph_node(node_id: str | None) -> None:
    init_chat_state()
    st.session_state["selected_graph_node"] = node_id or None


def get_selected_graph_node() -> str | None:
    init_chat_state()
    value = st.session_state.get("selected_graph_node")
    return str(value) if value else None


def set_selected_graph_filters(filters: dict[str, Any] | None) -> None:
    init_chat_state()
    st.session_state["selected_graph_filters"] = filters or {}


def get_selected_graph_filters() -> dict[str, Any]:
    init_chat_state()
    value = st.session_state.get("selected_graph_filters", {})
    return value if isinstance(value, dict) else {}


def set_selected_graph_chunks(chunk_ids: list[str] | None) -> None:
    init_chat_state()
    st.session_state["selected_graph_chunks"] = [str(item) for item in (chunk_ids or [])]


def get_selected_graph_chunks() -> list[str]:
    init_chat_state()
    value = st.session_state.get("selected_graph_chunks", [])
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def set_pinned_graph_nodes(node_ids: list[str] | None) -> None:
    init_chat_state()
    st.session_state["pinned_graph_nodes"] = [str(item) for item in (node_ids or [])]


def get_pinned_graph_nodes() -> list[str]:
    init_chat_state()
    value = st.session_state.get("pinned_graph_nodes", [])
    if isinstance(value, list):
        return [str(item) for item in value]
    return []
