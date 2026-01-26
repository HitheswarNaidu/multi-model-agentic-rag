import networkx as nx

from rag.chunking.metadata import ChunkMetadata, DocumentChunk
from rag.visualization.graph_builder import build_chunk_graph, add_cross_refs


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
    )
    return DocumentChunk(metadata=meta, content="text")


def test_build_chunk_graph_adds_doc_and_chunk_nodes():
    chunks = [make_chunk(1, "d1"), make_chunk(2, "d1")]
    G = build_chunk_graph(chunks)
    assert "doc:d1" in G.nodes
    assert "chunk:c1" in G.nodes
    assert any(edge for edge in G.edges if "doc:d1" in edge)


def test_add_cross_refs():
    chunks = [make_chunk(1, "d1"), make_chunk(2, "d2")]
    G = build_chunk_graph(chunks)
    add_cross_refs(G, [("chunk:c1", "chunk:c2")])
    assert G.has_edge("chunk:c1", "chunk:c2")
