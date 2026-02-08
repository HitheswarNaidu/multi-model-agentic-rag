from rag.agent.decomposer import Decomposer
from rag.generation.llm_client import MockLLMClient


def test_decomposer_logic():
    mock_payload = {
        "answer": "1. What is Apple's revenue?\n2. What is Microsoft's revenue?",
        "provenance": []
    }
    client = MockLLMClient(payload=mock_payload)
    dec = Decomposer(client)

    questions = dec.decompose("Compare Apple and Microsoft revenue")
    assert len(questions) == 2
    assert "Apple" in questions[0]
    assert "Microsoft" in questions[1]

