from rag.agent.memory import ConversationMemory
from rag.agent.query_rewriter import QueryRewriter
from rag.generation.llm_client import MockLLMClient


def test_memory_trimming():
    mem = ConversationMemory(max_turns=2)
    mem.add_user_message("1")
    mem.add_ai_message("a")
    mem.add_user_message("2")
    mem.add_ai_message("b")
    mem.add_user_message("3")
    mem.add_ai_message("c")

    # Should keep last 4 items (2 turns)
    assert len(mem.turns) == 4
    assert mem.turns[0].content == "2"

def test_rewriter_mock():
    # Mock LLM returns a rewritten query
    mock_response = {
        "answer": "What is the price of the iPhone?",
        "provenance": []
    }
    client = MockLLMClient(payload=mock_response)
    rewriter = QueryRewriter(client)
    mem = ConversationMemory()
    mem.add_user_message("I like the iPhone.")

    rewritten = rewriter.rewrite("How much is it?", mem)
    assert rewritten == "What is the price of the iPhone?"
