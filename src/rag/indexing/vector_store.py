from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

import chromadb
from chromadb import Client
from chromadb.api.types import EmbeddingFunction, Embeddings

from rag.chunking.metadata import DocumentChunk


class SentenceTransformerEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name: str = "all-mpnet-base-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def __call__(self, input: Sequence[str]) -> Embeddings:
        return self.model.encode(list(input), convert_to_numpy=True).tolist()


class VectorStore:
    def __init__(
        self,
        collection_name: str = "chunks",
        embedding_model: str = "all-mpnet-base-v2",
        client: Optional[Client] = None,
        embedding_fn: Optional[EmbeddingFunction] = None,
        collection=None,
        persist_directory: Optional[str] = None,
    ) -> None:
        if client is not None:
            self.client = client
        else:
            if persist_directory:
                # New-style persistent client (avoids deprecated chroma_db_impl settings)
                self.client = chromadb.PersistentClient(path=persist_directory)
            else:
                self.client = chromadb.Client()
        self.embedding_fn = embedding_fn or SentenceTransformerEmbeddingFunction(embedding_model)
        if collection is not None:
            self.collection = collection
        else:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )

    def index_documents(self, chunks: Iterable[DocumentChunk]) -> None:
        ids: List[str] = []
        texts: List[str] = []
        metadatas: List[dict] = []
        for chunk in chunks:
            ids.append(chunk.metadata.chunk_id)
            texts.append(chunk.content)
            metadatas.append(
                {
                    "doc_id": chunk.metadata.doc_id,
                    "doc_type": chunk.metadata.doc_type,
                    "chunk_type": chunk.metadata.chunk_type,
                    "page": chunk.metadata.page,
                    "section": chunk.metadata.section,
                }
            )
        if ids:
            self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas)

    def search(
        self,
        query: str,
        limit: int = 5,
        doc_type: Optional[str] = None,
        doc_id: Optional[str] = None,
        chunk_type: Optional[str] = None,
    ) -> List[dict]:
        where_filter = None
        if doc_type or doc_id or chunk_type:
            where_filter = {}
            if doc_type:
                where_filter["doc_type"] = doc_type
            if doc_id:
                where_filter["doc_id"] = doc_id
            if chunk_type:
                where_filter["chunk_type"] = chunk_type

        results = self.collection.query(query_texts=[query], n_results=limit, where=where_filter)
        matches: List[dict] = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        md = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        for idx, cid in enumerate(ids):
            meta = md[idx] or {}
            if doc_type and meta.get("doc_type") != doc_type:
                continue
            if doc_id and meta.get("doc_id") != doc_id:
                continue
            matches.append(
                {
                    "chunk_id": cid,
                    "content": docs[idx],
                    "score": 1 - distances[idx] if distances else None,
                    "metadata": meta,
                }
            )
        return matches
