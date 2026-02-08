
import pandas as pd
import streamlit as st


def render_chunk_table(chunks: list[dict]):
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

    st.dataframe(df, width="stretch")
    st.caption(f"Showing {len(df)} chunks")
