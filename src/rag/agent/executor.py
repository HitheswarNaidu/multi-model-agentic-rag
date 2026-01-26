from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rag.agent.planner import Plan, Planner
from rag.generation.llm_client import LLMClient
from rag.validation.validator import validate_answer


@dataclass
class ExecutionResult:
    plan: Plan
    results: List[dict]
    log: List[str] = field(default_factory=list)


class AgentExecutor:
    def __init__(self, planner: Planner, llm: LLMClient):
        self.planner = planner
        self.llm = llm

    def run(self, query: str, filters: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        plan = self.planner.make_plan(query, filters)
        log: List[str] = [f"intent={plan.intent}"]
        retrieval_results = self.planner.execute(plan, query, filters)
        log.append(f"retrieved={len(retrieval_results)}")

        contexts = [r.get("content", "") for r in retrieval_results][:8]
        llm_payload = self.llm.generate(contexts, query, intent=plan.intent)
        validation = validate_answer(llm_payload)
        if not validation.get("valid", False):
            log.append(f"validation_failed:{validation.get('issues')}")

        return ExecutionResult(plan=plan, results=retrieval_results, log=log)
