from rag.agent.intent_classifier import classify_intent


def test_intent_numeric():
    assert classify_intent("What is 123?") == "numeric_table"


def test_intent_image():
    assert classify_intent("show me the figure") == "image_related"


def test_intent_definition():
    assert classify_intent("what is RAG?") == "definition"


def test_intent_multi_hop():
    assert classify_intent("compare A and B") == "multi_hop"


def test_intent_general():
    assert classify_intent("hello world") == "general"
