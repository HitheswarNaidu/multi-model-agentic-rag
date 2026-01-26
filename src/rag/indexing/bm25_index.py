from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from whoosh import index
from whoosh.fields import ID, KEYWORD, Schema, TEXT
from whoosh.qparser import MultifieldParser
from whoosh.query import Term, And

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
            metadata=KEYWORD(stored=True, scorable=False, commas=True),
        )
        if index.exists_in(self.index_dir):
            self.ix = index.open_dir(self.index_dir)
        else:
            self.ix = index.create_in(self.index_dir, self.schema)

    def index_documents(self, chunks: Iterable[DocumentChunk]) -> None:
        writer = self.ix.writer()
        for chunk in chunks:
            meta = chunk.metadata
            metadata_pairs = {
                "doc_id": meta.doc_id,
                "doc_type": meta.doc_type,
                "chunk_type": meta.chunk_type,
                "page": str(meta.page),
                "section": meta.section,
            }
            writer.update_document(
                doc_id=meta.doc_id,
                chunk_id=meta.chunk_id,
                doc_type=meta.doc_type,
                chunk_type=meta.chunk_type,
                content=chunk.content,
                metadata=",".join(f"{k}:{v}" for k, v in metadata_pairs.items()),
            )
        writer.commit()

    def search(
        self,
        query: str,
        limit: int = 5,
        doc_type: Optional[str] = None,
        doc_id: Optional[str] = None,
        chunk_type: Optional[str] = None,
    ) -> List[dict]:
        qp = MultifieldParser(["content"], schema=self.schema)
        q = qp.parse(query)
        
        filter_q = None
        filters = []
        if doc_type:
            filters.append(Term("doc_type", doc_type))
        if doc_id:
            filters.append(Term("doc_id", doc_id))
        if chunk_type:
            filters.append(Term("chunk_type", chunk_type))
        
        if filters:
            if len(filters) == 1:
                filter_q = filters[0]
            else:
                filter_q = And(filters)

        results_out: List[dict] = []
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
                        "metadata": hit.get("metadata"),
                    }
                )
        return results_out
