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


def _node_matches(graph: nx.Graph, search: str) -> list[str]:
    needle = str(search or "").strip().casefold()
    if not needle:
        return list(graph.nodes())
    matches: list[str] = []
    for node, attrs in graph.nodes(data=True):
        hay = " ".join(
            [
                str(node),
                str(attrs.get("doc_id", "")),
                str(attrs.get("chunk_id", "")),
                str(attrs.get("section", "")),
                str(attrs.get("chunk_type", "")),
                str(attrs.get("content_preview", ""))[:200],
            ]
        ).casefold()
        if needle in hay:
            matches.append(str(node))
    return matches


def build_interactive_subgraph(
    graph: nx.Graph,
    selected_node: str | None,
    depth: int,
    focus_mode: bool,
    pinned_nodes: list[str] | None,
    edge_types: list[str] | None,
    search: str,
    max_nodes: int,
) -> tuple[nx.Graph, dict]:
    selected = graph.copy()
    allowed_edges = {str(item) for item in (edge_types or []) if str(item)}
    if allowed_edges:
        keep_edges = [
            (a, b)
            for a, b, attrs in selected.edges(data=True)
            if str(attrs.get("edge_type", "edge")) in allowed_edges
        ]
        edge_graph = nx.Graph()
        edge_graph.add_nodes_from(selected.nodes(data=True))
        edge_graph.add_edges_from(
            [(a, b, selected.get_edge_data(a, b) or {}) for a, b in keep_edges]
        )
        selected = edge_graph

    matches = _node_matches(selected, search)
    if search.strip():
        selected = selected.subgraph(matches).copy()

    focus_set = {str(item) for item in (pinned_nodes or []) if str(item)}
    if selected_node:
        focus_set.add(str(selected_node))

    if focus_mode and focus_set:
        frontier = set(focus_set)
        neighborhood = set(focus_set)
        hops = max(0, int(depth))
        for _ in range(hops):
            next_frontier: set[str] = set()
            for node in frontier:
                next_frontier.update(selected.neighbors(node) if node in selected else [])
            neighborhood.update(next_frontier)
            frontier = next_frontier
        selected = selected.subgraph(neighborhood).copy()
    elif selected_node and depth > 0 and selected_node in selected:
        neighborhood = {selected_node}
        frontier = {selected_node}
        for _ in range(int(depth)):
            next_frontier: set[str] = set()
            for node in frontier:
                next_frontier.update(selected.neighbors(node))
            neighborhood.update(next_frontier)
            frontier = next_frontier
        selected = selected.subgraph(neighborhood).copy()

    node_cap_hit = False
    if selected.number_of_nodes() > max_nodes:
        node_cap_hit = True
        kept = list(selected.nodes())[:max_nodes]
        selected = selected.subgraph(kept).copy()

    stats = {
        "nodes": selected.number_of_nodes(),
        "edges": selected.number_of_edges(),
        "node_cap_hit": node_cap_hit,
        "match_count": len(matches),
    }
    return selected, stats


def get_node_detail(graph: nx.Graph, node_id: str | None) -> dict:
    if not node_id or node_id not in graph:
        return {}
    attrs = graph.nodes[node_id]
    neighbors = list(graph.neighbors(node_id))
    related: list[dict[str, str]] = []
    for neighbor in neighbors[:20]:
        edge = graph.get_edge_data(node_id, neighbor) or {}
        related.append(
            {
                "neighbor": str(neighbor),
                "edge_type": str(edge.get("edge_type", "edge")),
                "reason": str(edge.get("reason", "")),
            }
        )
    return {
        "node_id": node_id,
        "node_type": attrs.get("node_type", ""),
        "doc_id": attrs.get("doc_id", ""),
        "chunk_id": attrs.get("chunk_id", ""),
        "page": attrs.get("page", ""),
        "section": attrs.get("section", ""),
        "chunk_type": attrs.get("chunk_type", ""),
        "semantic_group_id": attrs.get("semantic_group_id", ""),
        "content_preview": attrs.get("content_preview", ""),
        "neighbor_count": len(neighbors),
        "neighbors": neighbors[:100],
        "related": related,
    }
