from __future__ import annotations

from typing import Dict, List, Tuple, Optional


class ValidationResult(Dict):
    pass


def _numeric_tokens(text: str) -> List[str]:
    import re
    # Match numbers but strip trailing dots (e.g. "100." -> "100")
    matches = re.findall(r"[-+]?\d[\d,]*\.?\d+", text)
    # Also catch integer-only like "2023" but avoid matching in the middle of words if possible
    # Simplified: match chunks that look like numbers
    raw = re.findall(r"[-+]?\d[\d,\.]*", text)
    clean = []
    for r in raw:
        # Strip trailing dot if present (end of sentence)
        if r.endswith("."):
            r = r[:-1]
        if not r: continue
        clean.append(r)
    return clean


def _normalize_num(num: str) -> str:
    # Remove commas
    return num.replace(",", "")


def _numeric_with_units(text: str) -> List[tuple[str, str]]:
    import re

    # Capture number with optional pre-fix ($/£) OR post-fix (%, USD)
    # Group 1: Prefix ($)
    # Group 2: Number
    # Group 3: Postfix unit
    pattern = r"([$€£¥])?\s*([-+]?\d[\d,\.]*)\s*([%$]|[A-Za-z]+)?"
    matches = re.findall(pattern, text)
    results = []
    for prefix, num, suffix in matches:
        if not num: continue
        if num.endswith("."): num = num[:-1]
        if not num: continue
        
        unit = (prefix or "") + (suffix or "")
        results.append((num.replace(",", ""), unit))
    return results


def validate_answer(answer_payload: Dict, retrieval: Optional[List[Dict]] = None) -> ValidationResult:
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
    if len({ _normalize_num(n) for n in numeric_values }) > 1:
        result["issues"].append("numeric_multiple_values")

    if numeric_values and retrieval:
        retrieval_text = " ".join([r.get("content", "") for r in retrieval])
        if not any(num in retrieval_text for num in numeric_values):
            result["valid"] = False
            result["issues"].append("numeric_unsubstantiated")

        # Conflict: differing numeric values across retrieval docs
        seen = set(_normalize_num(n) for n in numeric_values)
        for r in retrieval:
            r_nums_units = _numeric_with_units(r.get("content", ""))
            for n, unit in r_nums_units:
                n_norm = _normalize_num(n)
                if n not in seen:
                    result["valid"] = False
                    result["issues"].append("numeric_conflict")
                    break

        # Unit conflicts: same number but differing units between answer and retrieval
        answer_nums_units = _numeric_with_units(answer_text)
        answer_units = {u for _, u in answer_nums_units if u}
        retrieval_units = {u for r in retrieval for _, u in _numeric_with_units(r.get("content", "")) if u}
        if answer_units and retrieval_units and answer_units.isdisjoint(retrieval_units):
            result["valid"] = False
            result["issues"].append("numeric_unit_conflict")

        # Context-aware numeric conflicts: if retrieval contains multiple distinct numeric values
        # for the same unit (or unitless) and the answer includes a numeric, flag conflict.
        retrieval_values_by_unit: Dict[str, set[str]] = {}
        for r in retrieval:
            for n, u in _numeric_with_units(r.get("content", "")):
                retrieval_values_by_unit.setdefault(u, set()).add(_normalize_num(n))

        answer_values_by_unit: Dict[str, set[str]] = {}
        for n, u in answer_nums_units:
            answer_values_by_unit.setdefault(u, set()).add(_normalize_num(n))

        for unit, retrieval_vals in retrieval_values_by_unit.items():
            if len(retrieval_vals) <= 1:
                continue
            answer_vals = answer_values_by_unit.get(unit, set())
            if answer_vals and (answer_vals & retrieval_vals):
                result["valid"] = False
                result["issues"].append("numeric_conflict_context")
                break

    if answer_payload.get("conflict", False):
        result["valid"] = False
        result["issues"].append("conflict_detected")

    # Placeholder: conflict detection could inspect multiple provenance contexts

    return result
