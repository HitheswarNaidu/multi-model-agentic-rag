# ruff: noqa: E402

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.utils.session import get_prewarm_status, start_pipeline_prewarm

st.set_page_config(page_title="Multimodal Agentic RAG", layout="wide")
start_pipeline_prewarm()

if hasattr(st, "switch_page"):
    st.switch_page("pages/1_💬_Chat.py")

st.title("Multimodal Agentic RAG")
st.caption("If you are not redirected automatically, open the Chat page from the sidebar.")
status = get_prewarm_status()
st.info(f"Warm-up status: {status.get('state', 'pending')}")
st.page_link("pages/1_💬_Chat.py", label="Open Chat", icon="💬")
