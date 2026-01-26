# RAG Edge Cases and Mitigations

One-page guide to common RAG failure modes, how to detect them, and how the agent should react with retrieval + validation + requery strategies.

## Common Problems
- **Vague or underspecified queries:** Missing entity, time, or scope.
- **Numeric/table lookups:** Numbers embedded in tables; unit mismatches; totals vs per-row ambiguity.
- **Conflicting sources:** Multiple chunks disagree; stale vs updated versions.
- **Sparse keyword hits:** Exact term exists only once; vector search may miss short strings.
- **Long tables/sections:** Chunking splits rows; pagination splits tables across pages.
- **Layout-sensitive content:** Headers/footers bleed into chunks; column order matters.
- **Multilingual/mixed scripts:** Embeddings weaker across languages; OCR noise.
- **Images/figures:** Key info in images; captions separated.
- **Temporal scope:** Data changes over time; query lacks date.
- **Provenance gaps:** Retrieved context doesn’t cover the answer fully.
- **Agent/tool loops:** Repeated tool calls without progress.

## Agent Playbook
1. **Classify intent:** numeric/table, definition, multi-hop, image-related, vague.
2. **Select strategy:**
   - Numeric/table → prioritize table_row_search + BM25 over table text; enforce unit checks.
   - Exact terms → BM25-first; apply metadata filters (doc_type/page/section/chunk_type).
   - Conceptual → vector-first; rerank with metadata boosts.
   - Vague → ask LLM to propose clarifying questions; or re-query with inferred constraints, but mark low confidence.
3. **Retrieval fusion:** use RRF/weighted scores; diversify sources (different pages/docs) before rerank.
4. **Validation:**
   - Check provenance covers each claim.
   - Numeric sanity (range/unit/consistency across chunks).
   - Conflict detection: if top chunks disagree, return INSUFFICIENT_DATA or present both with provenance.
5. **Retry policy:**
   - If low recall/conflict: widen filters, increase k, switch strategy (BM25↔vector), focus on tables.
   - If vague: surface clarifying question to user; avoid guessing.
   - If image-needed: flag and request OCR/vision path.

## Handling Vague Questions
- Detect missing dimensions (who/what/where/when/version/unit).
- Respond with a **clarifying question**; include a suggested scope based on top metadata (doc titles/sections).
- If answering, prepend “Low confidence” and provide provenance + reasons for uncertainty.

## Agentic Orchestration Edge Cases
- **Tool loops:** cap retries; change strategy on each retry (e.g., switch BM25→vector, adjust filters).
- **Empty/overlapping chunks:** fall back to larger window; ensure overlap for context but avoid duplicates in scoring.
- **Timeouts/slow indexes:** degrade gracefully to single best retriever with conservative k.
- **Missing provenance:** never emit answer without source; return INSUFFICIENT_DATA.

## Table-Specific Issues
- Per-row chunks: ensure row-level chunk_type and table_id; include header row in metadata.
- Cross-page tables: stitch adjacent page table chunks before answering.
- Units: normalize (%, $, currencies); warn when mixed units detected.
- Totals vs subtotals: detect “total/summary” tokens; prefer row context over isolated cells.

## Numeric and Dates
- Normalize numbers (thousands separators, percentages) before comparison.
- Date ambiguity (MM/DD vs DD/MM): detect format from doc locale; flag uncertainty if unclear.

## Conflicting Sources
- Present both values with provenance and note disagreement.
- Prefer newer doc versions if version/date metadata available; otherwise mark conflict.

## Output & Logging
- Always include provenance IDs and chunk metadata in answers.
- Save answers to `output/answers/` and agent/retrieval logs to `output/logs/` for audit.

## Quick Checklist for the Agent
- [ ] Is the query fully specified? If not, ask clarifying question.
- [ ] Did retrieval cover relevant tables/rows and text sections?
- [ ] Are numbers consistent and units aligned?
- [ ] Do sources conflict? If yes, present both or return INSUFFICIENT_DATA.
- [ ] Does every claim cite provenance?
- [ ] If confidence is low, say so and explain why.
