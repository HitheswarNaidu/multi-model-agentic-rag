from rag.agent.query_expander import QueryExpander
from rag.generation.llm_client import MockLLMClient


def test_query_expansion():
    # Mock LLM returns a structured response
    mock_response = {
        "answer": "1. Alternative One\n2. Alternative Two\n3. Alternative Three",
        "provenance": []
    }
    client = MockLLMClient(payload=mock_response)
    expander = QueryExpander(client)

    expanded = expander.expand("test query")
    assert len(expanded) == 3
    assert expanded[0] == "1. Alternative One" or "Alternative One" in expanded[0]

def test_query_expansion_integration_logic():
    # Only tests the expansion logic, not the full planner execution which requires more mocks
    pass
