# Agent Design – Multimodal Agentic RAG

## Purpose
The agent is the intelligent controller of the RAG pipeline. It dynamically decides how to search, combine, and validate information instead of using static retrieval.

## Responsibilities
- Understand user intent
- Select retrieval strategy
- Apply metadata filters
- Combine BM25 and vector results
- Rerank candidates
- Call LLM for synthesis
- Validate answers
- Retry when necessary

## Agent Components
### Intent Classifier
Determines query type:
- Numeric/table query
- Definition query
- Multi-hop reasoning
- Image-related query

### Planner
Maps intent to strategy:
- BM25-first
- Vector-first
- Hybrid parallel
- Table-row focused

### Tools Available to Agent
- bm25_search(query, filters)
- vector_search(query)
- hybrid_search(query)
- table_row_search(query)
- rerank(candidates)
- call_llm(contexts)
- validate(answer)

## Planner Logic
Example rules:
- If query contains numbers or currency → prioritize table chunks
- If query requires exact terms → BM25-first
- If query is conceptual → vector-first
- Otherwise → hybrid retrieval

## Retrieval Fusion
Results from BM25 and vector search are combined using:
- Reciprocal Rank Fusion
- Weighted normalized scoring
- Metadata boosts

## Reranking
- Optional cross-encoder model
- Metadata-priority ranking
- Diversity-aware selection

## LLM Interaction
Agent sends to LLM:
- Top ranked contexts
- Clear instructions
- Metadata-prefixed chunks

Expected LLM output:
{
  "answer": "...",
  "fields": {},
  "provenance": ["doc:chunk"]
}

## Validation Rules
- Numeric sanity checks
- Provenance existence
- Conflict detection
- Fallback to INSUFFICIENT_DATA when needed

## Retry Mechanism
If validation fails:
- Reformulate query
- Change retrieval mode
- Focus on table rows
- Increase top-k

## Logging and Explainability
Agent logs:
- intent
- strategy
- retrieved chunks
- scores
- LLM output
- validation result

## Example Workflow
1. User asks a question
2. Agent classifies intent
3. Planner selects hybrid retrieval
4. BM25 + Vector executed
5. Candidates reranked
6. LLM generates answer
7. Validator checks result
8. Final structured answer returned

## Boundaries
- Agent must not hallucinate
- Must always provide provenance
- Must not bypass metadata rules
- Must prefer evidence over creativity

## Outcome
The agent ensures that the RAG system is adaptive, explainable, accurate, context-aware, and reliable.
