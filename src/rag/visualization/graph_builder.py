from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

import networkx as nx

from rag.chunking.metadata import DocumentChunk


def _chunk_index(chunk_id: str) -> int:
    raw = str(chunk_id or "")
    tail = raw.rsplit("-", 1)[-1]
    digits = "".join(ch for ch in tail if ch.isdigit())
    return int(digits) if digits else 0


def build_chunk_graph(
    chunks: Iterable[DocumentChunk],
    include_doc_nodes: bool = True,
    include_edge_types: bool = True,
    include_semantic_edges: bool = True,
    include_adjacency_edges: bool = True,
    include_doc_similarity_edges: bool = True,
) -> nx.Graph:
    graph = nx.Graph()
    by_semantic_group: dict[str, list[str]] = defaultdict(list)
    by_page: dict[tuple[str, int], list[tuple[int, str]]] = defaultdict(list)
    doc_to_source_hash: dict[str, str] = {}

    for chunk in chunks:
        meta = chunk.metadata
        chunk_node = f"chunk:{meta.chunk_id}"
        chunk_attrs = {
            "node_type": "chunk",
            "type": "chunk",  # backward compatibility
            "doc_id": meta.doc_id,
            "chunk_id": meta.chunk_id,
            "page": meta.page,
            "section": meta.section,
            "chunk_type": meta.chunk_type,
            "semantic_group_id": meta.semantic_group_id,
            "source_hash": meta.source_hash or "",
            "content_preview": (chunk.content or "")[:400],
        }
        graph.add_node(chunk_node, **chunk_attrs)

        if meta.semantic_group_id:
            by_semantic_group[str(meta.semantic_group_id)].append(chunk_node)

        by_page[(meta.doc_id, int(meta.page or 0))].append(
            (_chunk_index(meta.chunk_id), chunk_node)
        )

        source_hash = str(meta.source_hash or "").strip()
        if source_hash:
            doc_to_source_hash[meta.doc_id] = source_hash

        if include_doc_nodes:
            doc_node = f"doc:{meta.doc_id}"
            if not graph.has_node(doc_node):
                graph.add_node(
                    doc_node,
                    node_type="doc",
                    type="doc",
                    doc_id=meta.doc_id,
                    chunk_id="",
                    page=0,
                    section="",
                    chunk_type="doc",
                    semantic_group_id="",
                    source_hash=source_hash,
                    content_preview="",
                )
            graph.add_edge(
                doc_node,
                chunk_node,
                edge_type="doc_chunk" if include_edge_types else "edge",
                weight=1.0,
                reason="chunk belongs to document",
            )

    if include_semantic_edges:
        for group_id, group_nodes in by_semantic_group.items():
            if len(group_nodes) < 2:
                continue
            ordered = sorted(group_nodes)
            for idx in range(len(ordered) - 1):
                left = ordered[idx]
                right = ordered[idx + 1]
                if left == right:
                    continue
                graph.add_edge(
                    left,
                    right,
                    edge_type="semantic_group" if include_edge_types else "edge",
                    weight=0.8,
                    reason=f"same semantic_group_id={group_id}",
                )

    if include_adjacency_edges:
        for ranked in by_page.values():
            if len(ranked) < 2:
                continue
            ranked_sorted = sorted(ranked, key=lambda item: item[0])
            for idx in range(len(ranked_sorted) - 1):
                left = ranked_sorted[idx][1]
                right = ranked_sorted[idx + 1][1]
                if left == right:
                    continue
                graph.add_edge(
                    left,
                    right,
                    edge_type="same_page_adjacent" if include_edge_types else "edge",
                    weight=0.5,
                    reason="adjacent chunk on same page",
                )

    if include_doc_similarity_edges and include_doc_nodes:
        hash_to_docs: dict[str, list[str]] = defaultdict(list)
        for doc_id, source_hash in doc_to_source_hash.items():
            hash_to_docs[source_hash].append(doc_id)

        for source_hash, docs in hash_to_docs.items():
            if len(docs) < 2:
                continue
            docs_sorted = sorted(docs)
            for idx in range(len(docs_sorted) - 1):
                left = f"doc:{docs_sorted[idx]}"
                right = f"doc:{docs_sorted[idx + 1]}"
                graph.add_edge(
                    left,
                    right,
                    edge_type="doc_similarity" if include_edge_types else "edge",
                    weight=0.3,
                    reason=f"shared source_hash={source_hash[:12]}",
                )

    return graph


def add_cross_refs(graph: nx.Graph, relations: list[tuple[str, str]]) -> nx.Graph:
    for src, dst in relations:
        graph.add_edge(src, dst, edge_type="xref", weight=0.4, reason="cross-reference")
    return graph
