import sys
from pathlib import Path
import json

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.components.chunk_viewer import render_chunk_table
from app.utils.session import get_pipeline

st.title("📊 Data Store Viewer")

pipeline = get_pipeline()
chunks = pipeline.saved_chunks()

if not chunks:
    st.info("No indexed chunks yet. Upload and process documents first.")
else:
    st.subheader("Indexed Chunks")
    render_chunk_table(chunks)

output_dir = Path("output/answers")
output_dir.mkdir(parents=True, exist_ok=True)
saved_answers = list(output_dir.glob("*.json"))
st.subheader("Saved Answers")
if saved_answers:
    for p in saved_answers:
        with st.expander(p.name):
            try:
                data = json.loads(p.read_text())
                st.json(data)
            except Exception as exc:
                st.warning(f"Could not read {p}: {exc}")
else:
    st.info("No saved answers yet.")
