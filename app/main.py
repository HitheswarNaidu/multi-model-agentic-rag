import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

st.set_page_config(page_title="Multimodal Agentic RAG", layout="wide")

st.title("Multimodal Agentic RAG Dashboard")
st.markdown("Use the left sidebar pages to navigate.")
