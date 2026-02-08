from __future__ import annotations

from dataclasses import dataclass

from rag.agent.decomposer import Decomposer
from rag.agent.hyde_generator import HydeGenerator
from rag.agent.intent_classifier import IntentType, classify_intent
from rag.agent.query_expander import QueryExpander
from rag.agent.summarizer import Summarizer
from rag.agent.tools import AgentTools
from rag.generation.llm_client import LLMClient
from rag.utils.date_extractor import DateExtractor


@dataclass
class PlanStep:
    tool: str
    k: int = 5
    note: str = ""


@dataclass
class Plan:
    intent: IntentType
    steps: list[PlanStep]


class Planner:
    def __init__(self, tools: AgentTools, llm_client: LLMClient | None = None):
        self.tools = tools
        self.expander = QueryExpander(llm_client) if llm_client else None
        self.summarizer = Summarizer(tools.bm25)
        self.decomposer = Decomposer(llm_client) if llm_client else None
        self.hyde = HydeGenerator(llm_client) if llm_client else None
        self.date_extractor = DateExtractor()
        self.enable_hyde = False
        self.enable_decomposition = False

    def set_deep_features(self, enable_hyde: bool, enable_decomposition: bool) -> None:
        self.enable_hyde = enable_hyde
        self.enable_decomposition = enable_decomposition

    def make_plan(self, query: str, filters: dict | None = None, mode: str = "default") -> Plan:
        intent = classify_intent(query)
        steps: list[PlanStep] = []

        # Check for temporal constraints
        years = self.date_extractor.extract_years(query)
        temporal_note = f"Focus on year(s): {', '.join(years)}" if years else ""

        if intent == "summarization":
            steps.append(PlanStep(tool="summarize_doc", k=1, note="Generate full doc summary"))
        elif intent == "numeric_table":
            steps.append(
                PlanStep(
                    tool="table_row_search",
                    k=8,
                    note=f"Prioritize table rows. {temporal_note}",
                )
            )
            steps.append(PlanStep(tool="bm25_search", k=5, note="Exact terms"))
        elif intent == "definition":
            steps.append(PlanStep(tool="bm25_search", k=6, note="Precise definitions"))
            steps.append(PlanStep(tool="vector_search", k=4, note="Semantic support"))
        elif intent == "multi_hop":
            steps.append(
                PlanStep(tool="hybrid_search", k=8, note=f"Diverse contexts. {temporal_note}")
            )
            steps.append(PlanStep(tool="bm25_search", k=4, note="Exact anchors"))
        elif intent == "image_related":
            steps.append(PlanStep(tool="hybrid_search", k=6, note="Figure captions if available"))
        elif intent == "clarification":
            # For vague queries, do a light search to help the LLM suggest a better scope
            steps.append(PlanStep(tool="bm25_search", k=3, note="Scout for relevant docs"))
        else:
            # General intent
            steps.append(PlanStep(tool="hybrid_search", k=6, note=f"General. {temporal_note}"))

        # Fast mode removes auxiliary expansion/decomposition complexity.
        if mode != "deep":
            filtered_steps = []
            for s in steps:
                if s.tool in {
                    "bm25_search",
                    "vector_search",
                    "hybrid_search",
                    "table_row_search",
                    "summarize_doc",
                }:
                    filtered_steps.append(s)
            steps = filtered_steps or [PlanStep(tool="hybrid_search", k=6, note="Fast default")]

        return Plan(intent=intent, steps=steps)

    def execute(
        self,
        plan: Plan,
        query: str,
        filters: dict | None = None,
        mode: str = "default",
    ) -> list[dict]:
        filters = filters or {}
        results: list[dict] = []

        # 1. Handle Multi-Hop Reasoning (deep mode only)
        if (
            mode == "deep"
            and self.enable_decomposition
            and plan.intent == "multi_hop"
            and self.decomposer
        ):
            sub_queries = self.decomposer.decompose(query)
            # Run search for each sub-query to gather diverse context
            for sq in sub_queries:
                # For sub-queries, we use a slightly more conservative k
                results.extend(self.tools.hybrid_search(sq, filters, k=5))

        # 2. Determine main queries to run (original + expanded)
        queries_to_run = [query]
        if mode == "deep" and self.expander and plan.intent in ("general", "clarification"):
            expanded = self.expander.expand(query)
            if expanded:
                queries_to_run.append(expanded[0])

        for q in queries_to_run:
            for step in plan.steps:
                if step.tool == "summarize_doc":
                    target_doc_id = ""
                    if filters and filters.get("doc_id"):
                        target_doc_id = str(filters["doc_id"])
                    elif filters and filters.get("doc_ids"):
                        doc_ids = [
                            str(item) for item in (filters.get("doc_ids") or []) if str(item)
                        ]
                        target_doc_id = doc_ids[0] if doc_ids else ""
                    if self.summarizer and target_doc_id:
                        results.extend(
                            self.summarizer.gather_document_chunks(target_doc_id, limit=64)
                        )
                    else:
                        results.extend(self.tools.hybrid_search(q, filters, k=10))
                elif step.tool == "bm25_search":
                    results.extend(self.tools.bm25_search(q, filters, k=step.k))
                elif step.tool == "vector_search":
                    # Use HyDE in deep mode to bridge semantic gap for vector retrieval.
                    search_query = q
                    if (
                        mode == "deep"
                        and self.enable_hyde
                        and self.hyde
                        and plan.intent in ("definition", "general")
                    ):
                        hypothetical = self.hyde.generate_hypothetical_document(q)
                        if hypothetical:
                            # Append hypothetical answer to boost semantic matching.
                            search_query = f"{q}\n{hypothetical}"

                    results.extend(self.tools.vector_search(search_query, filters, k=step.k))
                elif step.tool == "hybrid_search":
                    results.extend(self.tools.hybrid_search(q, filters, k=step.k))
                elif step.tool == "table_row_search":
                    results.extend(self.tools.table_row_search(q, filters, k=step.k))

        # Deduplicate results by chunk_id
        seen = set()
        unique_results: list[dict] = []
        for r in results:
            if r["chunk_id"] not in seen:
                seen.add(r["chunk_id"])
                unique_results.append(r)

        return unique_results
