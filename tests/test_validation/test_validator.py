from rag.validation.validator import validate_answer


def test_validation_requires_provenance():
    res = validate_answer({"answer": "42"})
    assert res["valid"] is False
    assert "missing_provenance" in res["issues"]


def test_validation_numeric_without_provenance():
    res = validate_answer({"answer": "Value is 123"})
    assert res["valid"] is False
    assert "numeric_without_provenance" in res["issues"]


def test_validation_conflict_flag():
    res = validate_answer({"answer": "A", "provenance": ["c1"], "conflict": True})
    assert res["valid"] is False
    assert "conflict_detected" in res["issues"]


def test_validation_ok():
    res = validate_answer({"answer": "hello", "provenance": ["c1"]})
    assert res["valid"] is True


def test_validation_numeric_unsubstantiated():
    res = validate_answer({"answer": "Value is 123", "provenance": ["c1"]}, retrieval=[{"content": "no numbers here"}])
    assert res["valid"] is False
    assert "numeric_unsubstantiated" in res["issues"]


def test_validation_numeric_unit_conflict():
    res = validate_answer(
        {"answer": "It is 10%", "provenance": ["c1"]},
        retrieval=[{"content": "It is 10 USD"}],
    )
    assert res["valid"] is False
    assert "numeric_unit_conflict" in res["issues"]


def test_validation_numeric_conflict_context():
    res = validate_answer(
        {"answer": "Value is 10", "provenance": ["c1"]},
        retrieval=[{"content": "Value is 10"}, {"content": "Value is 11"}],
    )
    assert res["valid"] is False
    assert "numeric_conflict_context" in res["issues"]
