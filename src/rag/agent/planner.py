from __future__ import annotations

from dataclasses import dataclass
from typing import List

from rag.agent.intent_classifier import IntentType, classify_intent
from rag.agent.tools import AgentTools
from rag.generation.llm_client import LLMClient
from rag.agent.query_expander import QueryExpander


@dataclass
class PlanStep:
    tool: str
    k: int = 5
    note: str = ""


@dataclass
class Plan:
    intent: IntentType
    steps: List[PlanStep]


class Planner:
    def __init__(self, tools: AgentTools, llm_client: LLMClient = None):
        self.tools = tools
        self.expander = QueryExpander(llm_client) if llm_client else None

    def make_plan(self, query: str, filters: dict | None = None) -> Plan:
        intent = classify_intent(query)
        steps: List[PlanStep] = []
        if intent == "numeric_table":
            steps.append(PlanStep(tool="table_row_search", k=8, note="Prioritize table rows"))
            steps.append(PlanStep(tool="bm25_search", k=5, note="Exact terms"))
        elif intent == "definition":
            steps.append(PlanStep(tool="bm25_search", k=6, note="Precise definitions"))
            steps.append(PlanStep(tool="vector_search", k=4, note="Semantic support"))
        elif intent == "multi_hop":
            steps.append(PlanStep(tool="hybrid_search", k=8, note="Diverse contexts"))
            steps.append(PlanStep(tool="bm25_search", k=4, note="Exact anchors"))
        elif intent == "image_related":
            steps.append(PlanStep(tool="hybrid_search", k=6, note="Figure captions if available"))
        elif intent == "clarification":
            # For vague queries, do a light search to help the LLM suggest a better scope
            steps.append(PlanStep(tool="bm25_search", k=3, note="Scout for relevant docs"))
        else:
            steps.append(PlanStep(tool="hybrid_search", k=6, note="General"))
        return Plan(intent=intent, steps=steps)

    def execute(self, plan: Plan, query: str, filters: dict | None = None) -> List[dict]:
        filters = filters or {}
        results: List[dict] = []
        
        # Determine queries to run (original + expanded)
        queries_to_run = [query]
        if self.expander and plan.intent in ("general", "clarification"):
            expanded = self.expander.expand(query)
            # Add top 1 expansion to keep latency reasonable
            if expanded:
                queries_to_run.append(expanded[0])

        for q in queries_to_run:
            for step in plan.steps:
                if step.tool == "bm25_search":
                    results.extend(self.tools.bm25_search(q, filters, k=step.k))
                elif step.tool == "vector_search":
                    results.extend(self.tools.vector_search(q, filters, k=step.k))
                elif step.tool == "hybrid_search":
                    results.extend(self.tools.hybrid_search(q, filters, k=step.k))
                elif step.tool == "table_row_search":
                    results.extend(self.tools.table_row_search(q, filters, k=step.k))
        
        # Deduplicate results by chunk_id
        seen = set()
        unique_results = []
        for r in results:
            if r["chunk_id"] not in seen:
                seen.add(r["chunk_id"])
                unique_results.append(r)
                
        return unique_results
