import streamlit as st
from typing import List, Dict
import pandas as pd

def render_chunk_table(chunks: List[Dict]):
    if not chunks:
        st.info("No chunks to display.")
        return

    df = pd.DataFrame(chunks)
    
    # Filter controls
    col1, col2 = st.columns(2)
    with col1:
        docs = ["All"] + sorted(df["doc_id"].unique().tolist())
        sel_doc = st.selectbox("Filter by Document", docs)
    with col2:
        types = ["All"] + sorted(df["chunk_type"].unique().tolist())
        sel_type = st.selectbox("Filter by Chunk Type", types)

    if sel_doc != "All":
        df = df[df["doc_id"] == sel_doc]
    if sel_type != "All":
        df = df[df["chunk_type"] == sel_type]

    st.dataframe(df, use_container_width=True)
    st.caption(f"Showing {len(df)} chunks")
