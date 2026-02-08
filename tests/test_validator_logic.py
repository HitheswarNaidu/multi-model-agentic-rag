from rag.validation.validator import validate_answer


def test_validator_basic_success():
    payload = {
        "answer": "The revenue is 500 million.",
        "provenance": ["chunk1"]
    }
    retrieval = [{"content": "Revenue reached 500 million last year."}]
    res = validate_answer(payload, retrieval)
    assert res["valid"] is True
    assert not res["issues"]

def test_validator_missing_provenance():
    payload = {
        "answer": "The revenue is 500.",
        "provenance": []
    }
    res = validate_answer(payload)
    assert res["valid"] is False
    assert "missing_provenance" in res["issues"]

def test_validator_numeric_mismatch():
    payload = {
        "answer": "The revenue is 600.",
        "provenance": ["chunk1"]
    }
    retrieval = [{"content": "Revenue was 500."}]
    res = validate_answer(payload, retrieval)
    assert res["valid"] is False
    assert "numeric_unsubstantiated" in res["issues"]

def test_validator_numeric_format_robustness():
    # Test 1,000 vs 1000
    payload = {
        "answer": "Total: 1,000",
        "provenance": ["c1"]
    }
    retrieval = [{"content": "Total is 1000."}]
    res = validate_answer(payload, retrieval)
    assert res["valid"] is True

def test_validator_conflict_flag():
    payload = {
        "answer": "It depends.",
        "provenance": ["c1"],
        "conflict": True
    }
    res = validate_answer(payload)
    assert res["valid"] is False
    assert "conflict_detected" in res["issues"]

def test_validator_currency_prefix():
    # Answer: $500. Retrieval: 500 USD.
    # Logic:
    # Answer parsed as (500, $)
    # Retrieval parsed as (500, USD)
    # Unit conflict? $ vs USD.
    # Current logic: checks if answer units and retrieval units are disjoint.
    # "$" and "USD" are disjoint strings. This might flag a false positive conflict.
    # However, let's just check extraction first.
    from rag.validation.validator import _numeric_with_units

    extracted = _numeric_with_units("$500")
    assert extracted == [("500", "$")]

    extracted2 = _numeric_with_units("500 USD")
    assert extracted2 == [("500", "USD")]

def test_validator_trailing_dot():
    from rag.validation.validator import _numeric_tokens

    tokens = _numeric_tokens("It was 100.")
    assert "100" in tokens
    assert "100." not in tokens
