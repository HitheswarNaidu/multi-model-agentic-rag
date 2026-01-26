# Multimodal Agentic RAG for Structured Document Analysis

## Overview
This project builds an intelligent Retrieval Augmented Generation (RAG) system designed for complex structured documents such as PDFs, invoices, reports, and forms. The system combines:

- Docling-based document parsing
- Smart metadata-aware chunking
- Hybrid retrieval using BM25 + Vector Search
- An agentic reasoning layer to plan retrieval strategies
- Large Language Model generation with provenance tracking

The goal is to answer user queries accurately from structured documents while preserving layout, tables, and contextual information.

## Problem Statement
Current document QA systems face multiple limitations:
- Most RAG systems treat documents as plain text and ignore tables, images, and layout.
- Naive chunking breaks semantic boundaries.
- Vector-only retrieval misses exact terms and numbers.
- Keyword-only retrieval lacks semantic understanding.
- Static RAG pipelines cannot reason or adapt.

These issues result in inaccurate answers and unreliable document understanding.

## Proposed Solution
The proposed system addresses these issues through:
- Multimodal parsing using Docling
- Metadata-first smart chunking
- Hybrid retrieval (BM25 + Vector)
- Agentic planning for dynamic retrieval
- Structured, provenance-backed answers

The system aims to outperform traditional RAG pipelines in accuracy, reliability, and explainability.

## System Architecture
High-level flow:
User Query → Agent Planner → Hybrid Retriever (BM25 + Vector + Metadata) → Reranker → LLM → Validator → Structured Answer

### Core Components
1. Ingestion Layer – Accepts PDFs, DOCX, and images
2. Parsing Layer – Docling converts documents into structured blocks
3. Chunking Layer – Logical metadata-aware chunk creation
4. Indexing Layer – BM25 index + Vector DB
5. Agent Layer – Decides retrieval strategy
6. Generation Layer – LLM answer synthesis
7. Validation Layer – Consistency and provenance checks

## Data Model and Metadata
Each chunk stored in the system contains:
- doc_id
- doc_type
- page
- section
- chunk_id
- chunk_type (paragraph, table, row, figure)
- table_id (if applicable)
- confidence score

### Metadata-First Chunk Format
Every stored chunk begins with metadata:

[doc_id: X] [page: Y] [section: Z] [chunk_type: table] <actual content>

This enables filtering, explainability, and better LLM grounding.

## Smart Chunking Strategy
- Section-based chunks
- Table-aware chunks
- Per-row table chunks
- Figure + caption chunks
- Overlap windows for long sections
- Logical boundary preservation

## Retrieval Strategy
### Hybrid Retrieval
- BM25 for exact matching
- Vector search for semantic similarity
- Fusion using weighted scoring or reciprocal rank fusion

### Metadata Filtering
Retrieval can be restricted by:
- document type
- page range
- section name
- chunk type

### Reranking
Optional cross-encoder reranker to improve top-k selection.

## LLM Generation Rules
- Use only retrieved context
- Always return structured JSON
- Provide provenance for each answer
- Return INSUFFICIENT_DATA when evidence is lacking

## Validation
- Numeric normalization
- Cross-check across multiple chunks
- Provenance verification
- Consistency checks

## Evaluation Plan
Metrics:
- Retrieval: MRR, Recall@k
- QA: Exact Match, F1
- Extraction: Field accuracy

Baselines:
- Text-only RAG
- Vector-only RAG
- Hybrid RAG without agent

Ablations:
- Without BM25
- Without metadata
- Without agentic planning

## Tech Stack
- Python
- Docling
- BM25 (Whoosh/ElasticSearch)
- FAISS/ChromaDB
- Sentence Transformers
- LangChain
- OpenAI / Local LLMs

## Deliverables
- Working prototype
- Evaluation results
- Research report
- Demo interface
