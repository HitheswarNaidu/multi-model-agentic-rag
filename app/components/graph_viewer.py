import streamlit as st
import tempfile

try:
    from pyvis.network import Network
except Exception:
    Network = None


def render_graph(graph):
    if graph is None or len(graph.nodes) == 0:
        st.info("No graph data available.")
        return

    if Network is None:
        st.warning("pyvis is not installed; graph rendering is unavailable.")
        return
    net = Network(height="600px", width="100%", notebook=False, bgcolor="#ffffff", font_color="#222222")
    for node, attrs in graph.nodes(data=True):
        color = "#6c9bd2" if attrs.get("type") == "doc" else "#f4a261"
        net.add_node(node, label=node, color=color)
    for src, dst, attrs in graph.edges(data=True):
        net.add_edge(src, dst, title=attrs.get("type", "edge"))
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.save_graph(tmp.name)
        html_content = open(tmp.name, "r", encoding="utf-8").read()
        st.components.v1.html(html_content, height=620)
