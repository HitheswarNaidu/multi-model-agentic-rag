import networkx as nx

from rag.visualization.graph_builder import build_interactive_subgraph


def test_node_cap_enforced_and_flagged():
    graph = nx.Graph()
    for idx in range(500):
        graph.add_node(
            f"chunk:c{idx}",
            node_type="chunk",
            doc_id="d1",
            chunk_id=f"c{idx}",
            page=1,
            section="",
            chunk_type="paragraph",
            content_preview="x",
        )
        if idx > 0:
            graph.add_edge(
                f"chunk:c{idx-1}",
                f"chunk:c{idx}",
                edge_type="same_page_adjacent",
                weight=0.5,
                reason="adj",
            )

    subgraph, stats = build_interactive_subgraph(
        graph=graph,
        selected_node=None,
        depth=0,
        focus_mode=False,
        pinned_nodes=[],
        edge_types=["same_page_adjacent"],
        search="",
        max_nodes=300,
    )
    assert subgraph.number_of_nodes() == 300
    assert stats["node_cap_hit"] is True
