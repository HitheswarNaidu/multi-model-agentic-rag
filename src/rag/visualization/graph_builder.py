from __future__ import annotations

import networkx as nx
from typing import Iterable, List, Optional

from rag.chunking.metadata import DocumentChunk


def build_chunk_graph(chunks: Iterable[DocumentChunk], include_doc_nodes: bool = True) -> nx.Graph:
    G = nx.Graph()
    for chunk in chunks:
        meta = chunk.metadata
        chunk_node = f"chunk:{meta.chunk_id}"
        G.add_node(chunk_node, type="chunk", doc_id=meta.doc_id, page=meta.page, section=meta.section, chunk_type=meta.chunk_type)
        if include_doc_nodes:
            doc_node = f"doc:{meta.doc_id}"
            if not G.has_node(doc_node):
                G.add_node(doc_node, type="doc", doc_id=meta.doc_id)
            G.add_edge(doc_node, chunk_node)
    return G


def add_cross_refs(graph: nx.Graph, relations: List[tuple[str, str]]) -> nx.Graph:
    for src, dst in relations:
        graph.add_edge(src, dst, type="xref")
    return graph
