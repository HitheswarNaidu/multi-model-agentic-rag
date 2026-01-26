import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.components.graph_viewer import render_graph
from app.utils.session import get_pipeline
from rag.visualization.graph_builder import build_chunk_graph
from rag.chunking.metadata import ChunkMetadata, DocumentChunk

st.title("🕸️ Document Graph")

pipeline = get_pipeline()
chunks_data = pipeline.saved_chunks()

if not chunks_data:
    st.info("No chunks indexed yet. Upload and process documents first.")
else:
    # Convert cached dicts back to DocumentChunk objects for graphing
    doc_chunks = [
        DocumentChunk(
            metadata=ChunkMetadata(
                doc_id=c["doc_id"],
                doc_type=c.get("doc_type", ""),
                page=c.get("page", 0),
                section=c.get("section", ""),
                chunk_id=c["chunk_id"],
                chunk_type=c.get("chunk_type", "paragraph"),
                table_id=None,
                confidence=1.0,
            ),
            content=c.get("content", ""),
        )
        for c in chunks_data
    ]
    graph = build_chunk_graph(doc_chunks, include_doc_nodes=True)
    render_graph(graph)
