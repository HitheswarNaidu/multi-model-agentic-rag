from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from itertools import islice

import chromadb
from chromadb import Client
from chromadb.api.types import EmbeddingFunction, Embeddings

from rag.chunking.metadata import DocumentChunk


class HashEmbeddingFunction(EmbeddingFunction):
    def __init__(self, dimension: int = 64) -> None:
        self.dimension = max(8, int(dimension))

    def __call__(self, input: Sequence[str]) -> Embeddings:
        embeddings: Embeddings = []
        for text in input:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            values = [float(byte) / 255.0 for byte in digest]
            repeats = (self.dimension // len(values)) + 1
            vector = (values * repeats)[: self.dimension]
            embeddings.append(vector)
        return embeddings

    @staticmethod
    def name() -> str:
        return "hash-embedding"

    def get_config(self) -> dict:
        return {"dimension": self.dimension}

    @staticmethod
    def build_from_config(config: dict):
        return HashEmbeddingFunction(dimension=int(config.get("dimension", 64)))


class NVIDIAEmbeddingFunction(EmbeddingFunction):
    def __init__(
        self,
        model_name: str = "nvidia/llama-nemotron-embed-1b-v2",
        api_key: str = "",
        truncate: str = "END",
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key
        self.truncate = truncate
        self._embedder = None

    def _get_embedder(self):
        if self._embedder is None:
            from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

            self._embedder = NVIDIAEmbeddings(
                model=self.model_name,
                api_key=self.api_key,
                truncate=self.truncate,
            )
        return self._embedder

    def __call__(self, input: Sequence[str]) -> Embeddings:
        embedder = self._get_embedder()
        return embedder.embed_documents(list(input))

    @staticmethod
    def name() -> str:
        return "nvidia-embedding"

    def get_config(self) -> dict:
        return {"model_name": self.model_name, "truncate": self.truncate}

    @staticmethod
    def build_from_config(config: dict):
        return NVIDIAEmbeddingFunction(
            model_name=config.get("model_name", "nvidia/llama-nemotron-embed-1b-v2"),
        )


class VectorStore:
    def __init__(
        self,
        collection_name: str = "chunks",
        embedding_model: str = "nvidia/llama-nemotron-embed-1b-v2",
        embedding_batch_size: int = 32,
        client: Client | None = None,
        embedding_fn: EmbeddingFunction | None = None,
        collection=None,
        persist_directory: str | None = None,
        nvidia_api_key: str = "",
    ) -> None:
        if client is not None:
            self.client = client
        else:
            if persist_directory:
                self.client = chromadb.PersistentClient(path=persist_directory)
            else:
                self.client = chromadb.Client()
        self.embedding_batch_size = max(1, int(embedding_batch_size))
        if embedding_fn is not None:
            self.embedding_fn = embedding_fn
        elif embedding_model == "hash-embedding":
            self.embedding_fn = HashEmbeddingFunction()
        else:
            self.embedding_fn = NVIDIAEmbeddingFunction(
                model_name=embedding_model,
                api_key=nvidia_api_key,
            )
        if collection is not None:
            self.collection = collection
        else:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )

    @staticmethod
    def _chunk_to_fields(chunk: DocumentChunk) -> tuple[str, str, dict]:
        return (
            chunk.metadata.chunk_id,
            chunk.content,
            {
                "doc_id": chunk.metadata.doc_id,
                "doc_type": chunk.metadata.doc_type,
                "chunk_type": chunk.metadata.chunk_type,
                "page": chunk.metadata.page,
                "section": chunk.metadata.section,
                "parent_content": chunk.metadata.parent_content or "",
                "source_path": chunk.metadata.source_path or "",
                "source_hash": chunk.metadata.source_hash or "",
                "ingest_timestamp_utc": chunk.metadata.ingest_timestamp_utc or "",
                "is_table": chunk.metadata.is_table,
                "is_image": chunk.metadata.is_image,
                "semantic_group_id": chunk.metadata.semantic_group_id or "",
                "boundary_reason": chunk.metadata.boundary_reason or "",
            },
        )

    @staticmethod
    def _chunked(items: Sequence[DocumentChunk], batch_size: int):
        iterator = iter(items)
        while True:
            batch = list(islice(iterator, batch_size))
            if not batch:
                break
            yield batch

    def index_documents(self, chunks: Iterable[DocumentChunk]) -> None:
        self.index_documents_batched(chunks, batch_size=self.embedding_batch_size)

    def index_documents_batched(
        self,
        chunks: Iterable[DocumentChunk],
        batch_size: int = 64,
    ) -> dict[str, float]:
        chunk_list = list(chunks)
        if not chunk_list:
            return {"indexed": 0, "upsert_batches": 0, "embed_ms": 0.0, "upsert_ms": 0.0}
        batch_size = max(1, int(batch_size))
        total_indexed = 0
        batch_count = 0
        total_embed_ms = 0.0
        total_upsert_ms = 0.0
        for batch in self._chunked(chunk_list, batch_size):
            metrics = self.upsert_chunk_batch(batch)
            total_indexed += int(metrics.get("indexed", 0))
            total_embed_ms += float(metrics.get("embed_ms", 0.0))
            total_upsert_ms += float(metrics.get("upsert_ms", 0.0))
            batch_count += 1
        return {
            "indexed": total_indexed,
            "upsert_batches": batch_count,
            "embed_ms": round(total_embed_ms, 2),
            "upsert_ms": round(total_upsert_ms, 2),
        }

    def upsert_chunk_batch(self, chunks: Sequence[DocumentChunk]) -> dict[str, float]:
        dedup: dict[str, tuple[str, dict]] = {}
        for chunk in chunks:
            cid, content, metadata = self._chunk_to_fields(chunk)
            dedup[cid] = (content, metadata)
        ids = list(dedup.keys())
        texts = [dedup[cid][0] for cid in ids]
        metadatas = [dedup[cid][1] for cid in ids]
        if not ids:
            return {"indexed": 0, "embed_ms": 0.0, "upsert_ms": 0.0}

        from time import perf_counter

        embed_t0 = perf_counter()
        embeddings = self.embedding_fn(texts)
        embed_ms = (perf_counter() - embed_t0) * 1000

        upsert_t0 = perf_counter()
        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        upsert_ms = (perf_counter() - upsert_t0) * 1000
        return {
            "indexed": len(ids),
            "embed_ms": round(embed_ms, 2),
            "upsert_ms": round(upsert_ms, 2),
        }

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
        chunk_ids_set = {str(item) for item in chunk_ids} if isinstance(chunk_ids, list) else set()
        doc_ids_set = {str(item) for item in doc_ids} if isinstance(doc_ids, list) else set()
        chunk_type = f.get("chunk_type", chunk_type)

        where_filter: dict[str, object] = {}
        if doc_type:
            where_filter["doc_type"] = doc_type
        if doc_ids:
            ids = [str(item) for item in doc_ids if str(item).strip()]
            if ids:
                where_filter["doc_id"] = {"$in": ids}
        elif doc_id:
            where_filter["doc_id"] = doc_id
        if chunk_type:
            where_filter["chunk_type"] = chunk_type
        for key in ["section", "source_hash", "ingest_timestamp_utc", "is_table", "is_image"]:
            if key in f and f[key] not in (None, ""):
                where_filter[key] = f[key]
        if "page" in f and f["page"] not in (None, ""):
            where_filter["page"] = int(f["page"])
        if not where_filter:
            where_filter = None

        query_embeddings = self.embedding_fn([query])
        results = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=limit,
            where=where_filter,
        )
        matches: list[dict] = []
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
            if doc_ids_set and str(meta.get("doc_id")) not in doc_ids_set:
                continue
            if chunk_ids_set and str(cid) not in chunk_ids_set:
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


class NoOpVectorStore:
    """BM25-only fallback when vector retrieval is disabled or unavailable."""

    def __init__(self, reason: str = "VECTOR_DISABLED") -> None:
        self.reason = reason
        self.embedding_fn = None

    def index_documents(self, chunks: Iterable[DocumentChunk]) -> None:
        _ = chunks
        return None

    def index_documents_batched(
        self,
        chunks: Iterable[DocumentChunk],
        batch_size: int = 64,
    ) -> dict[str, float]:
        _ = chunks
        _ = batch_size
        return {"indexed": 0, "upsert_batches": 0, "embed_ms": 0.0, "upsert_ms": 0.0}

    def upsert_chunk_batch(self, chunks: Sequence[DocumentChunk]) -> dict[str, float]:
        _ = chunks
        return {"indexed": 0, "embed_ms": 0.0, "upsert_ms": 0.0}

    def search(
        self,
        query: str,
        limit: int = 5,
        filters: dict | None = None,
        doc_type: str | None = None,
        doc_id: str | None = None,
        chunk_type: str | None = None,
    ) -> list[dict]:
        _ = query
        _ = limit
        _ = filters
        _ = doc_type
        _ = doc_id
        _ = chunk_type
        return []
