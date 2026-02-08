from rag.chunking.metadata import ChunkMetadata, DocumentChunk
from rag.visualization.graph_builder import add_cross_refs, build_chunk_graph


def make_chunk(idx: int, doc: str = "d1") -> DocumentChunk:
    meta = ChunkMetadata(
        doc_id=doc,
        doc_type="pdf",
        page=1,
        section="s",
        chunk_id=f"c{idx}",
        chunk_type="paragraph",
        table_id=None,
        confidence=0.9,
        semantic_group_id="g1" if idx in {1, 2} else "g2",
        source_hash="abc" if doc == "d1" else "xyz",
    )
    return DocumentChunk(metadata=meta, content="text")


def test_build_chunk_graph_adds_doc_and_chunk_nodes():
    chunks = [make_chunk(1, "d1"), make_chunk(2, "d1")]
    graph = build_chunk_graph(chunks)
    assert "doc:d1" in graph.nodes
    assert "chunk:c1" in graph.nodes
    assert any(edge for edge in graph.edges if "doc:d1" in edge)
    assert graph.nodes["chunk:c1"]["node_type"] == "chunk"
    assert graph["doc:d1"]["chunk:c1"]["edge_type"] == "doc_chunk"


def test_build_chunk_graph_adds_semantic_and_adjacency_edges():
    chunks = [make_chunk(1, "d1"), make_chunk(2, "d1"), make_chunk(3, "d1")]
    graph = build_chunk_graph(chunks)
    assert graph.has_edge("chunk:c1", "chunk:c2")
    assert graph["chunk:c1"]["chunk:c2"]["edge_type"] in {"semantic_group", "same_page_adjacent"}


def test_build_chunk_graph_adds_doc_similarity_edges():
    chunks = [make_chunk(1, "d1"), make_chunk(2, "d2")]
    chunks[1].metadata.source_hash = "abc"
    graph = build_chunk_graph(chunks)
    assert graph.has_edge("doc:d1", "doc:d2")
    assert graph["doc:d1"]["doc:d2"]["edge_type"] == "doc_similarity"


def test_add_cross_refs():
    chunks = [make_chunk(1, "d1"), make_chunk(2, "d2")]
    graph = build_chunk_graph(chunks)
    add_cross_refs(graph, [("chunk:c1", "chunk:c2")])
    assert graph.has_edge("chunk:c1", "chunk:c2")
