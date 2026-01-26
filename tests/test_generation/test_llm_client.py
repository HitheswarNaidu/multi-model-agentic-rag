from rag.generation.llm_client import MockLLMClient


def test_mock_llm_client_returns_payload():
    client = MockLLMClient(payload={"answer": "hello", "provenance": ["c1"]})
    resp = client.generate(["ctx"], "q")
    assert resp["answer"] == "hello"
    assert resp["provenance"] == ["c1"]


def test_mock_llm_client_defaults_provenance():
    client = MockLLMClient(payload={"answer": "hello"})
    resp = client.generate(["ctx"], "q")
    assert "provenance" in resp
    assert isinstance(resp["provenance"], list)
