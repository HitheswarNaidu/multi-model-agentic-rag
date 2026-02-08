from rag.generation.llm_client import LLMClient, MockLLMClient


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


def test_extract_json_payload_from_code_fence():
    payload = "```json\n{\n  \"answer\": \"ok\",\n  \"provenance\": [\"c1\"]\n}\n```"
    extracted = LLMClient._extract_json_payload(payload)
    assert extracted.startswith("{")
    assert '"answer"' in extracted


def test_extract_json_payload_from_plain_text():
    payload = "Here is output: {\"answer\":\"ok\",\"provenance\":[\"c1\"]} done"
    extracted = LLMClient._extract_json_payload(payload)
    assert extracted == '{"answer":"ok","provenance":["c1"]}'
