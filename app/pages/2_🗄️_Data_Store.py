# ruff: noqa: E402

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.utils.session import get_expert_mode, get_pipeline, set_expert_mode, start_pipeline_prewarm

st.set_page_config(page_title="Data Store | Multimodal Agentic RAG", layout="wide")
start_pipeline_prewarm()
pipeline = get_pipeline()

st.title("Data Store")
st.caption("Browse indexed documents, chunk metadata, and saved answers.")

expert_mode = st.toggle("Expert mode", value=get_expert_mode())
set_expert_mode(expert_mode)

chunks = pipeline.saved_chunks()
if not chunks:
    st.info("No indexed chunks yet. Upload and index files from the Chat page.")
else:
    df = pd.DataFrame(chunks)
    docs = sorted(df["doc_id"].dropna().unique().tolist()) if "doc_id" in df.columns else []
    types = (
        sorted(df["chunk_type"].dropna().unique().tolist())
        if "chunk_type" in df.columns
        else []
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Documents", len(docs))
    c2.metric("Chunks", len(df))
    c3.metric("Chunk types", len(types))

    with st.expander("Filters", expanded=True):
        selected_doc = st.selectbox("Document", ["All"] + docs)
        selected_type = st.selectbox("Chunk type", ["All"] + types)

    filtered = df.copy()
    if selected_doc != "All":
        filtered = filtered[filtered["doc_id"] == selected_doc]
    if selected_type != "All":
        filtered = filtered[filtered["chunk_type"] == selected_type]

    if not expert_mode:
        preferred_cols = [
            "doc_id",
            "doc_type",
            "chunk_id",
            "chunk_type",
            "page",
            "section",
            "ingest_timestamp_utc",
            "content",
        ]
        view_cols = [col for col in preferred_cols if col in filtered.columns]
        st.dataframe(filtered[view_cols], width="stretch")
    else:
        st.dataframe(filtered, width="stretch")

st.subheader("Saved Answers")
answers_dir = Path("output/answers")
answers_dir.mkdir(parents=True, exist_ok=True)
answer_files = sorted(answers_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

if not answer_files:
    st.info("No saved answers yet.")
else:
    for answer_file in answer_files[:50]:
        with st.expander(answer_file.name, expanded=False):
            try:
                payload = json.loads(answer_file.read_text(encoding="utf-8"))
            except Exception as exc:
                st.error(f"Failed to read {answer_file.name}: {exc}")
                continue
            if expert_mode:
                st.json(payload)
            else:
                st.markdown(payload.get("answer", "(no answer)"))
                citations = payload.get("provenance", [])
                if citations:
                    st.caption(f"Citations: {', '.join(str(c) for c in citations)}")
