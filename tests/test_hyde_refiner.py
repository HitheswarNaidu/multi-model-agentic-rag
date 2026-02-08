from rag.agent.hyde_generator import HydeGenerator
from rag.generation.llm_client import MockLLMClient
from rag.generation.refiner import Refiner


def test_hyde_generator():
    mock_payload = {"answer": "A hypothetical passage about quantum physics."}
    client = MockLLMClient(payload=mock_payload)
    hyde = HydeGenerator(client)

    doc = hyde.generate_hypothetical_document("What is entanglement?")
    assert doc == "A hypothetical passage about quantum physics."

def test_refiner_logic():
    # Mock specific response for refinement
    # In reality, MockLLMClient returns the payload['answer'], but refiner expects a JSON structure
    # or falls back if it gets text.

    # Case 1: Refiner makes corrections
    mock_payload = {
        "answer": '{"refined_answer": "Corrected text", "corrections_made": true}',
        "provenance": []
    }
    client = MockLLMClient(payload=mock_payload)
    refiner = Refiner(client)

    # We patch the json loading logic inside LLMClient by using a smart mock or just relying on
    # the fact that our MockLLMClient returns a dict, but LLMClient.generate returns a dict.
    # The Refiner calls llm.generate.
    # MockLLMClient.generate returns self.payload directly.
    # So if we set payload to contain the keys refiner expects, it works.

    # However, LLMClient.generate parses JSON from the text.
    # Let's adjust the MockLLMClient usage or the test.
    # Actually, the Refiner expects `llm.generate` to return a dict.
    # If `llm.generate` returns `{"answer": "..."}`, Refiner parses that.

    # Let's mock the Refiner's internal call or just test that it handles the response dict.
    # For this unit test, let's assume LLMClient works and returns the dict we want.

    res = refiner.refine_answer("q", ["ctx"], "draft")
    # Our MockLLMClient returns `{"answer": ...}`.
    # The Refiner code checks `if "answer" in response`.
    # It interprets response["answer"] as the refined text.

    assert res["refined_answer"] == '{"refined_answer": "Corrected text", "corrections_made": true}'
    # Wait, the logic in Refiner is:
    # response = self.llm.generate(...)
    # if "answer" in response: return {"refined_answer": response["answer"], ...}

    # So if we want to test the "success" path where LLM returns proper JSON:
    # We need MockLLMClient to return a dict that DOES NOT have "answer" but HAS "refined_answer"?
    # But MockLLMClient *always* returns a dict with "answer" (default).

    # Let's make a custom mock for this test.
    class CustomMock:
        def generate(self, contexts, query):
            return {"refined_answer": "Better Answer", "corrections_made": True}

    refiner = Refiner(CustomMock())
    res = refiner.refine_answer("q", ["ctx"], "draft")
    assert res["refined_answer"] == "Better Answer"
    assert res["corrections_made"] is True

