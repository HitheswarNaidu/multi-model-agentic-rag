import networkx as nx

from rag.visualization.graph_builder import build_interactive_subgraph, get_node_detail


def _make_graph() -> nx.Graph:
    g = nx.Graph()
    g.add_node(
        "doc:d1",
        node_type="doc",
        doc_id="d1",
        chunk_id="",
        page=0,
        section="",
        chunk_type="doc",
        content_preview="",
    )
    g.add_node(
        "chunk:c1",
        node_type="chunk",
        doc_id="d1",
        chunk_id="c1",
        page=1,
        section="s1",
        chunk_type="paragraph",
        content_preview="hello world",
    )
    g.add_node(
        "chunk:c2",
        node_type="chunk",
        doc_id="d1",
        chunk_id="c2",
        page=1,
        section="s2",
        chunk_type="paragraph",
        content_preview="another chunk",
    )
    g.add_edge("doc:d1", "chunk:c1", edge_type="doc_chunk", weight=1.0, reason="belongs")
    g.add_edge("chunk:c1", "chunk:c2", edge_type="same_page_adjacent", weight=0.5, reason="adj")
    return g


def test_node_detail_and_hop_expansion():
    graph = _make_graph()
    subgraph, stats = build_interactive_subgraph(
        graph=graph,
        selected_node="chunk:c1",
        depth=1,
        focus_mode=False,
        pinned_nodes=[],
        edge_types=["doc_chunk", "same_page_adjacent"],
        search="",
        max_nodes=300,
    )
    assert subgraph.number_of_nodes() == 3
    assert stats["node_cap_hit"] is False
    detail = get_node_detail(subgraph, "chunk:c1")
    assert detail["node_id"] == "chunk:c1"
    assert detail["neighbor_count"] == 2


def test_focus_mode_with_pinned_nodes():
    graph = _make_graph()
    subgraph, _stats = build_interactive_subgraph(
        graph=graph,
        selected_node=None,
        depth=1,
        focus_mode=True,
        pinned_nodes=["chunk:c2"],
        edge_types=["same_page_adjacent", "doc_chunk"],
        search="",
        max_nodes=300,
    )
    assert "chunk:c2" in subgraph.nodes
