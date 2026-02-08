from __future__ import annotations


class ValidationResult(dict):
    pass


def _numeric_tokens(text: str) -> list[str]:
    import re
    pattern = re.compile(r"(?<![\w.])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")
    return pattern.findall(text)


def _normalize_num(num: str) -> str:
    # Remove commas
    return num.replace(",", "")


def _numeric_with_units(text: str) -> list[tuple[str, str]]:
    import re

    # Capture number with optional prefix currency or suffix unit.
    pattern = r"([$€£¥])?\s*([-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*([%]|[A-Za-z]{1,6})?"
    matches = re.findall(pattern, text)
    results = []
    for prefix, num, suffix in matches:
        if not num:
            continue
        unit = (prefix or "") + (suffix or "")
        results.append((num.replace(",", ""), unit))
    return results


def _normalize_unit(unit: str) -> str:
    u = (unit or "").strip().upper()
    if u in {"$", "USD"}:
        return "USD"
    if u in {"€", "EUR"}:
        return "EUR"
    if u in {"£", "GBP"}:
        return "GBP"
    if u in {"¥", "JPY"}:
        return "JPY"
    return u


def validate_answer(answer_payload: dict, retrieval: list[dict] | None = None) -> ValidationResult:
    result: ValidationResult = {"valid": True, "issues": []}
    if not answer_payload:
        result["valid"] = False
        result["issues"].append("empty_payload")
        return result

    provenance = answer_payload.get("provenance", []) or []
    if not provenance:
        result["valid"] = False
        result["issues"].append("missing_provenance")

    answer_text = str(answer_payload.get("answer", ""))
    numeric_values = _numeric_tokens(answer_text)
    if numeric_values and not provenance:
        result["valid"] = False
        result["issues"].append("numeric_without_provenance")

    # If answer contains multiple distinct numbers, flag potential conflict
    if len({_normalize_num(n) for n in numeric_values}) > 1:
        result["issues"].append("numeric_multiple_values")

    if numeric_values and retrieval:
        retrieval_text = " ".join([r.get("content", "") for r in retrieval])
        answer_norm = {_normalize_num(n) for n in numeric_values}
        retrieval_norm = {_normalize_num(n) for n in _numeric_tokens(retrieval_text)}
        if answer_norm and not (answer_norm & retrieval_norm):
            result["valid"] = False
            result["issues"].append("numeric_unsubstantiated")

        # Unit conflicts: same number but differing units between answer and retrieval
        answer_nums_units = _numeric_with_units(answer_text)
        answer_units = {_normalize_unit(u) for _, u in answer_nums_units if u}
        retrieval_units = {
            _normalize_unit(u)
            for r in retrieval
            for _, u in _numeric_with_units(r.get("content", ""))
            if u
        }
        if answer_units and retrieval_units and answer_units.isdisjoint(retrieval_units):
            result["valid"] = False
            result["issues"].append("numeric_unit_conflict")

        # If retrieval context contains competing numeric values and the answer picks one,
        # mark as conflicting context.
        if len(retrieval_norm) > 1 and (answer_norm & retrieval_norm):
            result["valid"] = False
            result["issues"].append("numeric_conflict_context")

    if answer_payload.get("conflict", False):
        result["valid"] = False
        result["issues"].append("conflict_detected")

    # Placeholder: conflict detection could inspect multiple provenance contexts

    return result
