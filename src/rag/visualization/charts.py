import plotly.express as px
import pandas as pd
from typing import List, Dict


def chunk_type_distribution(chunks: List[Dict]) -> px.pie:
    df = pd.DataFrame(chunks)
    if df.empty:
        df = pd.DataFrame([{"chunk_type": "none"}])
    return px.pie(df, names="chunk_type", title="Chunk Types")


def document_stats(chunks: List[Dict]) -> px.bar:
    df = pd.DataFrame(chunks)
    if df.empty:
        df = pd.DataFrame([{"doc_id": "none", "count": 0}])
    else:
        df = df.groupby("doc_id").size().reset_index(name="count")
    return px.bar(df, x="doc_id", y="count", title="Chunks per Document")
