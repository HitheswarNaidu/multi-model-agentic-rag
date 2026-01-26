from rag.visualization.charts import chunk_type_distribution, document_stats


def test_chunk_type_distribution_handles_empty():
    fig = chunk_type_distribution([])
    assert fig is not None


def test_document_stats_groups_by_doc():
    data = [
        {"doc_id": "d1", "chunk_type": "paragraph"},
        {"doc_id": "d1", "chunk_type": "paragraph"},
        {"doc_id": "d2", "chunk_type": "table"},
    ]
    fig = document_stats(data)
    assert fig is not None
