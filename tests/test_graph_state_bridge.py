import app.utils.session as session


def test_graph_state_bridge_roundtrip(monkeypatch):
    monkeypatch.setattr(session.st, "session_state", {})
    session.init_chat_state()

    session.set_selected_graph_node("chunk:c1")
    session.set_selected_graph_filters({"doc_ids": ["d1"]})
    session.set_selected_graph_chunks(["c1", "c2"])
    session.set_pinned_graph_nodes(["chunk:c1"])

    assert session.get_selected_graph_node() == "chunk:c1"
    assert session.get_selected_graph_filters() == {"doc_ids": ["d1"]}
    assert session.get_selected_graph_chunks() == ["c1", "c2"]
    assert session.get_pinned_graph_nodes() == ["chunk:c1"]
