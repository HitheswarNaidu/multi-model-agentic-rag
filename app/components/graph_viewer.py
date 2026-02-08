from __future__ import annotations

import tempfile

import networkx as nx
import streamlit as st

try:
    import plotly.graph_objects as go
except Exception:
    go = None

try:
    from pyvis.network import Network
except Exception:
    Network = None


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


def _render_graph_2d_force(graph: nx.Graph, show_labels: bool) -> None:
    if Network is None:
        st.warning("pyvis is not installed; 2D force graph rendering is unavailable.")
        return
    net = Network(
        height="660px",
        width="100%",
        notebook=False,
        bgcolor="#ffffff",
        font_color="#222222",
    )
    for node, attrs in graph.nodes(data=True):
        color = "#6c9bd2" if attrs.get("node_type") == "doc" else "#f4a261"
        net.add_node(node, label=node if show_labels else "", color=color)
    for src, dst, attrs in graph.edges(data=True):
        edge_type = str(attrs.get("edge_type", "edge"))
        width = 3 if edge_type == "doc_chunk" else 1.5
        net.add_edge(src, dst, title=edge_type, width=width)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.save_graph(tmp.name)
        with open(tmp.name, encoding="utf-8") as html_file:
            html_content = html_file.read()
        st.components.v1.html(html_content, height=680)


def _render_graph_3d_force(graph: nx.Graph, show_labels: bool) -> None:
    if go is None:
        st.warning("Plotly is not installed; 3D graph rendering is unavailable.")
        return
    positions = nx.spring_layout(graph, dim=3, seed=42, k=0.9)
    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    edge_z: list[float | None] = []
    for src, dst in graph.edges():
        x0, y0, z0 = positions[src]
        x1, y1, z1 = positions[dst]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_z.extend([z0, z1, None])

    node_x: list[float] = []
    node_y: list[float] = []
    node_z: list[float] = []
    node_color: list[str] = []
    node_text: list[str] = []
    for node, attrs in graph.nodes(data=True):
        x, y, z = positions[node]
        node_x.append(x)
        node_y.append(y)
        node_z.append(z)
        node_color.append("#6c9bd2" if attrs.get("node_type") == "doc" else "#f4a261")
        node_text.append(
            "<br>".join(
                [
                    f"id: {node}",
                    f"type: {attrs.get('node_type', '')}",
                    f"doc: {attrs.get('doc_id', '')}",
                    f"page: {attrs.get('page', '')}",
                    f"chunk_type: {attrs.get('chunk_type', '')}",
                ]
            )
        )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter3d(
            x=edge_x,
            y=edge_y,
            z=edge_z,
            mode="lines",
            line=dict(color="#8ea0b6", width=2),
            hoverinfo="none",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter3d(
            x=node_x,
            y=node_y,
            z=node_z,
            mode="markers",
            marker=dict(size=8, color=node_color),
            hovertext=node_text,
            hoverinfo="text",
            showlegend=False,
        )
    )
    fig.update_layout(
        margin=dict(l=0, r=0, b=0, t=0),
        scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False)),
        height=680,
    )
    st.plotly_chart(fig, width="stretch")


def _render_graph_radial(graph: nx.Graph, show_labels: bool) -> None:
    if go is None:
        st.warning("Plotly is not installed; radial graph rendering is unavailable.")
        return
    positions = nx.circular_layout(graph)
    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    for src, dst in graph.edges():
        x0, y0 = positions[src]
        x1, y1 = positions[dst]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    node_x = [positions[node][0] for node in graph.nodes()]
    node_y = [positions[node][1] for node in graph.nodes()]
    node_color = [
        "#6c9bd2" if graph.nodes[node].get("node_type") == "doc" else "#f4a261"
        for node in graph.nodes()
    ]
    node_labels = [node if show_labels else "" for node in graph.nodes()]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(color="#8ea0b6", width=1),
            hoverinfo="none",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text" if show_labels else "markers",
            text=node_labels,
            textposition="top center",
            marker=dict(size=10, color=node_color),
            hoverinfo="text",
            showlegend=False,
        )
    )
    fig.update_layout(
        margin=dict(l=0, r=0, b=0, t=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=680,
    )
    st.plotly_chart(fig, width="stretch")


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


def render_graph(
    graph: nx.Graph,
    mode: str,
    selected_node: str | None,
    depth: int,
    focus_mode: bool,
    pinned_nodes: list[str] | None,
    edge_types: list[str] | None,
    search: str,
    max_nodes: int = 300,
    show_labels: bool = True,
) -> tuple[nx.Graph, dict]:
    subgraph, stats = build_interactive_subgraph(
        graph=graph,
        selected_node=selected_node,
        depth=depth,
        focus_mode=focus_mode,
        pinned_nodes=pinned_nodes,
        edge_types=edge_types,
        search=search,
        max_nodes=max(20, int(max_nodes)),
    )
    if mode in {"3D force", "3D"}:
        _render_graph_3d_force(subgraph, show_labels=show_labels)
    elif mode == "radial":
        _render_graph_radial(subgraph, show_labels=show_labels)
    else:
        _render_graph_2d_force(subgraph, show_labels=show_labels)
    return subgraph, stats
