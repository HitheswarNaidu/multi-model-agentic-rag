from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from rag.agent.planner import Plan, Planner
from rag.generation.llm_client import LLMClient
from rag.generation.refiner import Refiner
from rag.validation.validator import validate_answer


@dataclass
class ExecutionResult:
    plan: Plan
    results: list[dict]
    llm_payload: dict[str, Any]
    validation: dict[str, Any]
    plan_ms: float
    retrieval_ms: float
    llm_ms: float
    validation_ms: float
    error: dict[str, Any] | None = None
    log: list[str] = field(default_factory=list)


class AgentExecutor:
    def __init__(self, planner: Planner, llm: LLMClient):
        self.planner = planner
        self.llm = llm
        self.refiner = Refiner(llm)

    @staticmethod
    def _classify_llm_error_code(error_message: str) -> str:
        text = str(error_message or "").lower()
        if "resource_exhausted" in text or ("quota" in text and "429" in text):
            return "LLM_QUOTA_EXHAUSTED"
        return "LLM_GENERATION_FAILED"

    @staticmethod
    def _fallback_payload(
        retrieval_results: list[dict],
        error_message: str,
        error_code: str,
    ) -> dict[str, Any]:
        provenance: list[str] = []
        if error_code != "LLM_QUOTA_EXHAUSTED":
            provenance = [r.get("chunk_id") for r in retrieval_results if r.get("chunk_id")][:2]
        answer = "INSUFFICIENT_DATA: language model unavailable. Please retry."
        if error_code == "LLM_QUOTA_EXHAUSTED":
            answer = (
                "LLM quota exhausted. Unable to generate an answer right now. "
                "Retry later or configure a higher quota API key."
            )
        return {
            "answer": answer,
            "provenance": provenance,
            "conflict": False,
            "error": {
                "code": error_code,
                "message": error_message,
            },
        }

    def run(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        mode: str = "default",
    ) -> ExecutionResult:
        plan_t0 = perf_counter()
        plan = self.planner.make_plan(query, filters, mode=mode)
        plan_ms = (perf_counter() - plan_t0) * 1000

        log: list[str] = [f"intent={plan.intent}"]

        retrieval_t0 = perf_counter()
        retrieval_results = self.planner.execute(plan, query, filters, mode=mode)
        retrieval_ms = (perf_counter() - retrieval_t0) * 1000
        log.append(f"retrieved={len(retrieval_results)}")

        contexts = [
            f"[{r.get('chunk_id', 'unknown')}] {r.get('content', '')}"
            for r in retrieval_results
        ][:8]
        llm_t0 = perf_counter()
        llm_error: dict[str, Any] | None = None
        try:
            llm_payload = self.llm.generate(contexts, query, intent=plan.intent)
        except Exception as exc:
            error_code = self._classify_llm_error_code(str(exc))
            llm_error = {
                "code": error_code,
                "message": str(exc),
            }
            llm_payload = self._fallback_payload(retrieval_results, str(exc), error_code=error_code)
            log.append(f"llm_fallback:{error_code}")

        if (
            plan.intent == "summarization"
            and retrieval_results
            and not (llm_payload.get("provenance", []) or [])
            and llm_error is None
        ):
            llm_error = {
                "code": "SUMMARY_PROVENANCE_MISSING",
                "message": "Summary output is missing provenance chunk ids.",
            }
            llm_payload = {
                "answer": "INSUFFICIENT_DATA",
                "provenance": [],
                "conflict": False,
                "error": llm_error,
            }
            log.append("summary_provenance_missing")

        # Refine step (deep mode only)
        if (
            mode == "deep"
            and contexts
            and llm_payload.get("answer")
            and llm_error is None
        ):
            refined = self.refiner.refine_answer(query, contexts, llm_payload["answer"])
            if refined.get("corrections_made"):
                llm_payload["answer"] = refined["refined_answer"]
                log.append("answer_refined")
        llm_ms = (perf_counter() - llm_t0) * 1000

        validation_t0 = perf_counter()
        validation = validate_answer(llm_payload, retrieval_results)
        validation_ms = (perf_counter() - validation_t0) * 1000
        if not validation.get("valid", False):
            log.append(f"validation_failed:{validation.get('issues')}")

        return ExecutionResult(
            plan=plan,
            results=retrieval_results,
            llm_payload=llm_payload,
            validation=validation,
            plan_ms=plan_ms,
            retrieval_ms=retrieval_ms,
            llm_ms=llm_ms,
            validation_ms=validation_ms,
            error=llm_error,
            log=log,
        )
