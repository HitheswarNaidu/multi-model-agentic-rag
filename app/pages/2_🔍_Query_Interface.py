import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.utils.session import get_pipeline

st.title("🔍 Query Interface")

pipeline = get_pipeline()

# Build doc options from cached chunks (after indexing)
doc_ids = sorted({c.get("doc_id") for c in pipeline.saved_chunks() if c.get("doc_id")})
doc_label_to_id = {"All documents": None}
doc_label_to_id.update({f"{doc_id}": doc_id for doc_id in doc_ids})
selected_label = st.selectbox("Limit to a specific document (optional)", list(doc_label_to_id.keys()))
selected_doc_id = doc_label_to_id[selected_label]

query = st.text_input("Ask a question")
run = st.button("Run Query")

if run and query:
    resp = pipeline.query(query, filters={"doc_id": selected_doc_id} if selected_doc_id else None)
    llm_payload = resp.get("llm", {})
    st.subheader("Answer")
    st.write(llm_payload.get("answer", "(no answer)"))
    prov = llm_payload.get("provenance", []) or []
    if prov:
        st.caption("Provenance")
        st.write("\n".join(str(p) for p in prov))

    st.subheader("Retrieval (top)")
    retrieval = resp.get("retrieval", [])[:5]
    if retrieval:
        cols = ["doc_id", "chunk_id", "chunk_type", "score", "hybrid_score", "content"]
        display_rows = []
        for r in retrieval:
            row = {k: r.get(k) for k in cols}
            display_rows.append(row)
        st.dataframe(display_rows)
    else:
        st.info("No retrieval results.")

    st.subheader("Validation")
    st.json(resp.get("validation", {}))

    if resp.get("answer_path"):
        st.caption(f"Saved to {resp['answer_path']}")

    st.subheader("Log")
    st.write(resp.get("log", []))
elif run:
    st.warning("Please enter a question.")
