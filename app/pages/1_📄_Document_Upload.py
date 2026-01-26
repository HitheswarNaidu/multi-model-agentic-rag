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

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

st.title("📄 Index Documents")

st.write("Drop files into:")
st.code(str(UPLOAD_DIR.resolve()))

files = sorted([p for p in UPLOAD_DIR.rglob("*") if p.is_file()])
st.subheader("Detected Files")
if files:
    for p in files[:50]:
        st.write(p.name)
else:
    st.info("No files found in data/uploads yet.")

process = st.button("Index data/uploads")
if process:
    pipeline = get_pipeline()
    summary = pipeline.ingest_uploads()
    st.success(
        f"Indexed {summary.get('files_indexed', 0)}/{summary.get('files_detected', 0)} files "
        f"({summary.get('chunks_indexed', 0)} chunks)."
    )
    errs = summary.get("errors", []) or []
    if errs:
        st.warning(f"{len(errs)} file(s) failed during indexing.")
        st.json(errs)
