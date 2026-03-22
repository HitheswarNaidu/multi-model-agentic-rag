from unittest.mock import patch

import pytest

from rag.generation.llm_client import (
    LLMClient,
    LLMQuotaExhaustedError,
    MockLLMClient,
    RateLimitError,
)


def test_mock_client():
    mock = MockLLMClient(payload={"answer": "test", "provenance": []})
    result = mock.generate([], "query")
    assert result["answer"] == "test"
    assert result["provenance"] == []


def test_parse_chain():
    client = LLMClient.__new__(LLMClient)
    chain = client._parse_chain(
        "groq:llama-3.3-70b-versatile,openrouter:meta-llama/llama-3.3-70b-instruct:free"
    )
    assert len(chain) == 2
    assert chain[0] == ("groq", "llama-3.3-70b-versatile")
    assert chain[1] == ("openrouter", "meta-llama/llama-3.3-70b-instruct:free")


def test_parse_chain_empty():
    client = LLMClient.__new__(LLMClient)
    chain = client._parse_chain("")
    assert chain == []


@patch.object(LLMClient, "_call_provider")
def test_first_provider_succeeds(mock_call):
    mock_call.return_value = {"answer": "from groq", "provenance": [], "conflict": False}
    client = LLMClient(
        groq_api_key="gsk_test",
        openrouter_api_key="sk-or-test",
        fallback_chain="groq:model-a,openrouter:model-b",
    )
    result = client.generate([], "test query")
    assert result["answer"] == "from groq"
    assert result["_llm_provider"] == "groq"
    assert result["_llm_fallback_used"] is False


@patch.object(LLMClient, "_call_provider")
def test_fallback_on_rate_limit(mock_call):
    mock_call.side_effect = [
        RateLimitError("429 rate limited"),
        {"answer": "from fallback", "provenance": [], "conflict": False},
    ]
    client = LLMClient(
        groq_api_key="gsk_test",
        openrouter_api_key="sk-or-test",
        fallback_chain="groq:model-a,openrouter:model-b",
    )
    result = client.generate([], "test query")
    assert result["answer"] == "from fallback"
    assert result["_llm_provider"] == "openrouter"
    assert result["_llm_fallback_used"] is True


@patch.object(LLMClient, "_call_provider")
def test_all_exhausted_raises(mock_call):
    mock_call.side_effect = RateLimitError("429")
    client = LLMClient(
        groq_api_key="gsk_test",
        openrouter_api_key="sk-or-test",
        fallback_chain="groq:model-a,openrouter:model-b",
    )
    with pytest.raises(LLMQuotaExhaustedError):
        client.generate([], "test query")


def test_extract_json_payload():
    client = LLMClient.__new__(LLMClient)
    # Test JSON in markdown fence
    text = '```json\n{"answer": "hello"}\n```'
    assert '"hello"' in client._extract_json_payload(text)
    # Test raw JSON
    text2 = '{"answer": "world"}'
    assert '"world"' in client._extract_json_payload(text2)
    # Test empty
    assert client._extract_json_payload("") == "{}"
