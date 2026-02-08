from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from whoosh import index
from whoosh.fields import ID, KEYWORD, TEXT, Schema
from whoosh.qparser import MultifieldParser
from whoosh.query import And, Or, Term

from rag.chunking.metadata import DocumentChunk


class BM25Index:
    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.schema = Schema(
            doc_id=ID(stored=True),
            chunk_id=ID(stored=True, unique=True),
            doc_type=ID(stored=True),
            chunk_type=ID(stored=True),
            content=TEXT(stored=True),
            parent_content=TEXT(stored=True), # Store parent context but don't index it for search
            metadata=KEYWORD(stored=True, scorable=False, commas=True),
        )
        if index.exists_in(self.index_dir):
            self.ix = index.open_dir(self.index_dir)
        else:
            self.ix = index.create_in(self.index_dir, self.schema)

    @staticmethod
    def _doc_fields(chunk: DocumentChunk) -> dict[str, str]:
        meta = chunk.metadata
        metadata_pairs = {
            "doc_id": meta.doc_id,
            "doc_type": meta.doc_type,
            "chunk_type": meta.chunk_type,
            "page": str(meta.page),
            "section": meta.section,
            "source_path": meta.source_path or "",
            "source_hash": meta.source_hash or "",
            "ingest_timestamp_utc": meta.ingest_timestamp_utc or "",
            "is_table": str(meta.is_table),
            "is_image": str(meta.is_image),
            "semantic_group_id": meta.semantic_group_id or "",
            "boundary_reason": meta.boundary_reason or "",
        }
        return {
            "doc_id": meta.doc_id,
            "chunk_id": meta.chunk_id,
            "doc_type": meta.doc_type,
            "chunk_type": meta.chunk_type,
            "content": chunk.content,
            "parent_content": meta.parent_content or "",
            "metadata": json.dumps(metadata_pairs),
        }

    def open_writer(self):
        return self.ix.writer()

    def add_documents_to_writer(self, writer, chunks: Iterable[DocumentChunk]) -> int:
        count = 0
        for chunk in chunks:
            writer.update_document(**self._doc_fields(chunk))
            count += 1
        return count

    @staticmethod
    def commit_writer(writer) -> None:
        writer.commit()

    def index_documents(self, chunks: Iterable[DocumentChunk]) -> None:
        writer = self.open_writer()
        self.add_documents_to_writer(writer, chunks)
        self.commit_writer(writer)

    @staticmethod
    def _parse_metadata(raw: str | None) -> dict[str, str]:
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
        out: dict[str, str] = {}
        for part in str(raw).split(","):
            if ":" not in part:
                continue
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
        return out

    def search(
        self,
        query: str,
        limit: int = 5,
        filters: dict | None = None,
        doc_type: str | None = None,
        doc_id: str | None = None,
        chunk_type: str | None = None,
    ) -> list[dict]:
        f = filters or {}
        doc_type = f.get("doc_type", doc_type)
        doc_id = f.get("doc_id", doc_id)
        doc_ids = f.get("doc_ids", None)
        chunk_ids = f.get("chunk_ids", None)
        chunk_type = f.get("chunk_type", chunk_type)

        qp = MultifieldParser(["content"], schema=self.schema)
        q = qp.parse(query)

        filter_q = None
        filters = []
        if doc_type:
            filters.append(Term("doc_type", doc_type))
        if doc_ids:
            terms = [Term("doc_id", str(item)) for item in doc_ids if str(item).strip()]
            if terms:
                filters.append(Or(terms))
        elif doc_id:
            filters.append(Term("doc_id", doc_id))
        if chunk_type:
            filters.append(Term("chunk_type", chunk_type))
        if chunk_ids:
            terms = [Term("chunk_id", str(item)) for item in chunk_ids if str(item).strip()]
            if terms:
                filters.append(Or(terms))

        if filters:
            if len(filters) == 1:
                filter_q = filters[0]
            else:
                filter_q = And(filters)

        results_out: list[dict] = []
        with self.ix.searcher() as searcher:
            res = searcher.search(q, filter=filter_q, limit=limit)
            for hit in res:
                results_out.append(
                    {
                        "doc_id": hit["doc_id"],
                        "chunk_id": hit["chunk_id"],
                        "doc_type": hit.get("doc_type"),
                        "chunk_type": hit.get("chunk_type"),
                        "score": hit.score,
                        "content": hit["content"],
                        "metadata": self._parse_metadata(hit.get("metadata")),
                        "parent_content": hit.get("parent_content"),
                    }
                )
        return results_out

    def get_chunks_by_doc_id(self, doc_id: str, limit: int = 64) -> list[dict]:
        if not doc_id:
            return []
        limit = max(1, int(limit))
        rows: list[dict] = []
        with self.ix.searcher() as searcher:
            for idx, hit in enumerate(searcher.documents(doc_id=doc_id)):
                if idx >= limit:
                    break
                rows.append(
                    {
                        "doc_id": hit.get("doc_id"),
                        "chunk_id": hit.get("chunk_id"),
                        "doc_type": hit.get("doc_type"),
                        "chunk_type": hit.get("chunk_type"),
                        "score": None,
                        "content": hit.get("content", ""),
                        "metadata": self._parse_metadata(hit.get("metadata")),
                        "parent_content": hit.get("parent_content"),
                    }
                )
        return rows
