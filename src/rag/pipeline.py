from __future__ import annotations

import hashlib
import json
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from rag.agent.executor import AgentExecutor
from rag.agent.memory import ConversationMemory
from rag.agent.planner import Planner
from rag.agent.query_rewriter import QueryRewriter
from rag.agent.tools import AgentTools
from rag.chunking.chunker import chunk_blocks
from rag.config import get_settings
from rag.generation.llm_client import LLMClient, MockLLMClient
from rag.indexing.bm25_index import BM25Index
from rag.indexing.hybrid_retriever import HybridRetriever
from rag.indexing.vector_store import NoOpVectorStore, VectorStore
from rag.ingestion.loader import iter_documents
from rag.ingestion.parser import LlamaParseError, parse_document
from rag.utils.audit_logger import AuditLogger, hash_query, new_request_id, utc_now_iso
from rag.utils import database as db
from rag.utils.index_registry import IndexRegistry
from rag.utils.job_store import JobStore

DATA_DIR = Path("data")
UPLOAD_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "indices"
OUTPUT_DIR = Path("output")
ANSWERS_DIR = OUTPUT_DIR / "answers"
LOGS_DIR = OUTPUT_DIR / "logs"


class Pipeline:
    def __init__(self, lazy_init: bool = True) -> None:
        self.settings = get_settings()
        for d in [UPLOAD_DIR, PROCESSED_DIR, INDEX_DIR, ANSWERS_DIR, LOGS_DIR]:
            d.mkdir(parents=True, exist_ok=True)
        self.bm25: BM25Index | None = None
        self.vector: VectorStore | NoOpVectorStore | None = None
        self.hybrid: HybridRetriever | None = None
        self.tools: AgentTools | None = None
        self.llm: LLMClient | MockLLMClient | None = None
        self.planner: Planner | None = None
        self.executor: AgentExecutor | None = None
        self.memory = ConversationMemory()
        self.rewriter: QueryRewriter | None = None

        self.cached_chunks: list[dict] = []
        jobs_file = INDEX_DIR / "ingestion_jobs.jsonl"
        registry_file = INDEX_DIR / "index_registry.json"
        self.index_registry = IndexRegistry(registry_file, INDEX_DIR)
        self.index_registry.ensure_initialized()
        self.job_store = JobStore(jobs_file)
        self.audit_logger = AuditLogger(LOGS_DIR / "events.jsonl")

        # Initialize SQLite database
        db_path = DATA_DIR / "rag.db"
        db.init_db(db_path)
        self._migrate_existing_data_to_sqlite()
        self._job_threads: dict[str, threading.Thread] = {}
        self._thread_lock = threading.Lock()
        self._runtime_lock = threading.Lock()
        self._runtime_ready = False
        self._active_index_id: str | None = None
        if not lazy_init:
            self._ensure_runtime_initialized()

    def _migrate_existing_data_to_sqlite(self) -> None:
        """One-time migration of file-based data into SQLite. Skips if already populated."""
        try:
            existing = db.fetchone("SELECT COUNT(*) as n FROM chunks")
            if existing and existing["n"] > 0:
                return  # Already migrated
        except Exception:
            return

        import logging
        logger = logging.getLogger(__name__)
        try:
            active = self.index_registry.get_active()
            catalog_path = Path(active["chunk_catalog"])
            stats = db.migrate_from_files(
                chunk_catalog_path=catalog_path,
                jobs_jsonl_path=INDEX_DIR / "ingestion_jobs.jsonl",
                events_jsonl_path=LOGS_DIR / "events.jsonl",
                answers_dir=ANSWERS_DIR,
                logs_dir=LOGS_DIR,
            )
            if any(v > 0 for v in stats.values()):
                logger.info("Migrated existing data to SQLite: %s", stats)
        except Exception as exc:
            logger.warning("SQLite migration skipped: %s", exc)

    def _ensure_runtime_initialized(self) -> None:
        if self._runtime_ready:
            return
        with self._runtime_lock:
            if self._runtime_ready:
                return
            self._enforce_index_integrity_on_startup()
            active_paths = self.index_registry.get_active()
            self.bm25 = BM25Index(Path(active_paths["bm25_dir"]))
            self.vector = self._build_vector_store(
                persist_directory=str(active_paths["vector_dir"]),
                mode="runtime",
            )
            self.hybrid = HybridRetriever(
                self.bm25,
                self.vector,
                enable_reranker=self.settings.reranker_enabled,
            )
            if isinstance(self.vector, NoOpVectorStore):
                self.hybrid.weight_bm25 = 1.0
                self.hybrid.weight_vector = 0.0
            self.tools = AgentTools(self.bm25, self.vector, self.hybrid)
            has_llm_key = bool(self.settings.groq_api_key or self.settings.openrouter_api_key)
            self.llm = (
                LLMClient(
                    groq_api_key=self.settings.groq_api_key,
                    openrouter_api_key=self.settings.openrouter_api_key,
                    fallback_chain=self.settings.llm_fallback_chain,
                )
                if has_llm_key
                else MockLLMClient()
            )
            self.planner = Planner(self.tools, self.llm)
            self.planner.set_deep_features(
                enable_hyde=self.settings.hyde_enabled,
                enable_decomposition=self.settings.decomposition_enabled,
            )
            self.executor = AgentExecutor(self.planner, self.llm)
            self.rewriter = QueryRewriter(self.llm)
            self._active_index_id = active_paths["index_id"]
            self._runtime_ready = True

    def _catalog_contains_demo_markers(
        self,
        rows: list[dict],
    ) -> tuple[bool, list[str], int]:
        reasons: list[str] = []
        marker_hits = 0
        doc_ids = {
            str(row.get("doc_id", "")).strip().casefold()
            for row in rows
            if isinstance(row, dict)
        }
        if "doc1" in doc_ids:
            reasons.append("doc_id:doc1")
        markers = [
            str(item).strip().casefold()
            for item in self.settings.demo_index_markers
            if str(item).strip()
        ]
        for row in rows:
            if not isinstance(row, dict):
                continue
            content = str(row.get("content", "") or "").casefold()
            chunk_id = str(row.get("chunk_id", "") or "").casefold()
            for marker in markers:
                if marker and (marker in content or marker == chunk_id):
                    marker_hits += 1
            if chunk_id.startswith("doc1-"):
                marker_hits += 1
        if marker_hits > 0:
            reasons.append("demo_marker_match")
        return (len(reasons) > 0, reasons, marker_hits)

    def _inspect_index_payload(self, payload: dict) -> dict:
        catalog_path = Path(str(payload.get("chunk_catalog", "")))
        rows = self._read_chunk_catalog(catalog_path)
        suspicious, reasons, marker_hits = self._catalog_contains_demo_markers(rows)
        return {
            "index_id": str(payload.get("index_id", "unknown")),
            "catalog_path": str(catalog_path),
            "rows": len(rows),
            "suspicious": bool(suspicious),
            "reasons": reasons,
            "marker_hits": int(marker_hits),
        }

    def _list_version_payloads(self) -> list[dict]:
        versions_root = INDEX_DIR / "versions"
        if not versions_root.exists():
            return []
        payloads: list[dict] = []
        for item in versions_root.iterdir():
            if not item.is_dir():
                continue
            index_id = item.name
            payloads.append(
                {
                    "index_id": index_id,
                    "bm25_dir": str((item / "bm25").resolve()),
                    "vector_dir": str((item / "vector").resolve()),
                    "chunk_catalog": str((item / "chunk_catalog.jsonl").resolve()),
                    "mtime": item.stat().st_mtime,
                }
            )
        payloads.sort(key=lambda x: float(x.get("mtime", 0.0)), reverse=True)
        return payloads

    def _find_latest_clean_index_payload(self) -> dict | None:
        for payload in self._list_version_payloads():
            info = self._inspect_index_payload(payload)
            if not info["suspicious"] and info["rows"] > 0:
                clean = dict(payload)
                clean.pop("mtime", None)
                clean["integrity"] = info
                return clean
        return None

    def _enforce_index_integrity_on_startup(self) -> None:
        if not bool(getattr(self.settings, "ignore_test_demo_indexes", True)):
            return
        try:
            active = self.index_registry.get_active()
            inspected = self._inspect_index_payload(active)
            self.audit_logger.log_event(
                "index_integrity_checked",
                mode="startup",
                quality={
                    "index_id": inspected["index_id"],
                    "rows": inspected["rows"],
                    "suspicious": inspected["suspicious"],
                    "marker_hits": inspected["marker_hits"],
                },
            )
            if not inspected["suspicious"]:
                return

            self.audit_logger.log_event(
                "index_integrity_flagged",
                mode="startup",
                quality={
                    "index_id": inspected["index_id"],
                    "reasons": inspected["reasons"],
                    "rows": inspected["rows"],
                },
                error={
                    "code": "INDEX_INTEGRITY_SUSPICIOUS",
                    "message": "Active index appears to contain demo/test artifacts.",
                },
            )
            latest_clean = self._find_latest_clean_index_payload()
            if latest_clean and latest_clean.get("index_id") != active.get("index_id"):
                switched = self.index_registry.set_active(latest_clean)
                self.cached_chunks = []
                self.audit_logger.log_event(
                    "index_auto_switched",
                    mode="startup",
                    quality={
                        "from_index_id": active.get("index_id"),
                        "to_index_id": switched["active"]["index_id"],
                        "reason": "auto_switch_to_clean_index",
                    },
                )
        except Exception as exc:
            self.audit_logger.log_event(
                "index_integrity_flagged",
                mode="startup",
                error={
                    "code": "INDEX_INTEGRITY_CHECK_FAILED",
                    "message": str(exc),
                },
            )

    def _build_vector_store(
        self,
        persist_directory: str,
        mode: str,
    ) -> VectorStore | NoOpVectorStore:
        if not bool(self.settings.vector_enabled):
            self.audit_logger.log_event(
                "vector_backend_disabled",
                mode=mode,
                error={
                    "code": "VECTOR_DISABLED",
                    "message": "Vector retrieval disabled by config.",
                },
                quality={"embedding_model": self.settings.embedding_model},
            )
            return NoOpVectorStore(reason="VECTOR_DISABLED")
        try:
            return VectorStore(
                persist_directory=persist_directory,
                embedding_model=self.settings.embedding_model,
                embedding_batch_size=self.settings.embedding_batch_size,
                nvidia_api_key=self.settings.nvidia_api_key,
            )
        except Exception as exc:
            self.settings.vector_enabled = False
            self.audit_logger.log_event(
                "vector_backend_disabled",
                mode=mode,
                error={"code": "VECTOR_INIT_FAILED", "message": str(exc)},
                quality={"embedding_model": self.settings.embedding_model},
            )
            return NoOpVectorStore(reason=str(exc))

    def warm_up(self) -> dict:
        warm_t0 = perf_counter()
        self.audit_logger.log_event("warmup_started", mode="startup")
        try:
            self._ensure_runtime_initialized()
            duration_ms = round((perf_counter() - warm_t0) * 1000, 2)
            self.audit_logger.log_event(
                "warmup_finished",
                mode="startup",
                durations_ms={"total_ms": duration_ms},
            )
            return {"status": "ready", "duration_ms": duration_ms}
        except Exception as exc:
            duration_ms = round((perf_counter() - warm_t0) * 1000, 2)
            self.audit_logger.log_event(
                "warmup_failed",
                mode="startup",
                durations_ms={"total_ms": duration_ms},
                error={"code": "WARMUP_FAILURE", "message": str(exc)},
            )
            return {"status": "failed", "duration_ms": duration_ms, "error": str(exc)}

    @staticmethod
    def _chunk_to_record(chunk) -> dict:
        return {
            "doc_id": chunk.metadata.doc_id,
            "doc_type": chunk.metadata.doc_type,
            "chunk_id": chunk.metadata.chunk_id,
            "chunk_type": chunk.metadata.chunk_type,
            "page": chunk.metadata.page,
            "section": chunk.metadata.section,
            "source_path": chunk.metadata.source_path,
            "source_hash": chunk.metadata.source_hash,
            "ingest_timestamp_utc": chunk.metadata.ingest_timestamp_utc,
            "is_table": chunk.metadata.is_table,
            "is_image": chunk.metadata.is_image,
            "semantic_group_id": chunk.metadata.semantic_group_id,
            "boundary_reason": chunk.metadata.boundary_reason,
            "content": chunk.content,
        }

    @staticmethod
    def _write_chunk_catalog(records: list[dict], catalog_path: Path) -> None:
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        with catalog_path.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=True) + "\n")

    @staticmethod
    def _read_chunk_catalog(catalog_path: Path) -> list[dict]:
        if not catalog_path.exists():
            return []
        rows: list[dict] = []
        with catalog_path.open("r", encoding="utf-8") as f:
            for line in f:
                text = line.strip()
                if not text:
                    continue
                try:
                    rows.append(json.loads(text))
                except json.JSONDecodeError:
                    continue
        return rows

    def _active_catalog_path(self) -> Path:
        active = self.index_registry.get_active()
        return Path(active["chunk_catalog"])

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _unique_upload_path(filename: str) -> Path:
        safe_name = Path(filename).name
        target = UPLOAD_DIR / safe_name
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix
        for idx in range(1, 10_000):
            candidate = UPLOAD_DIR / f"{stem}_{idx}{suffix}"
            if not candidate.exists():
                return candidate
        return UPLOAD_DIR / f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"

    def save_uploaded_files(self, uploaded_files: list[object]) -> list[Path]:
        saved: list[Path] = []
        for item in uploaded_files:
            name = str(getattr(item, "name", "") or "").strip()
            if not name:
                continue
            target = self._unique_upload_path(name)
            data: bytes
            if hasattr(item, "getbuffer"):
                data = bytes(item.getbuffer())
            elif hasattr(item, "getvalue"):
                data = bytes(item.getvalue())
            elif hasattr(item, "read"):
                data = item.read()
            else:
                continue
            target.write_bytes(data)
            saved.append(target)
        return saved

    def parse_chunk_parallel(
        self,
        job_id: str,
        files: list[Path],
        chunk_size: int,
        chunk_overlap: int,
        enable_hierarchy: bool,
        chunking_mode: str,
        progress_cb: Callable[[dict], None] | None = None,
    ) -> dict:
        files_detected = len(files)
        parsed_outputs: list[dict] = []
        errors: list[dict] = []
        file_statuses: list[dict] = []
        chunks_indexed = 0
        files_indexed = 0
        processed_files = 0
        parse_total_ms = 0.0
        chunk_total_ms = 0.0

        max_workers = max(
            1,
            min(
                self.settings.ingestion_parse_workers,
                self.settings.ingestion_parse_queue_size,
                max(1, files_detected),
            ),
        )

        def _parse_one(order_idx: int, path: Path) -> dict:
            parse_t0 = perf_counter()
            parsed = parse_document(path, settings=self.settings)
            parse_ms = (perf_counter() - parse_t0) * 1000
            parse_meta = parsed.parse_meta if isinstance(parsed.parse_meta, dict) else {}
            self.audit_logger.log_event(
                "parser_strategy_selected",
                job_id=job_id,
                mode="ingestion",
                quality={
                    "file": str(path),
                    "strategy": parse_meta.get("parser_strategy", "llamaparse"),
                    "parser_used": parse_meta.get("parser_used"),
                    "text_chars": parse_meta.get("text_chars", 0),
                },
                durations_ms={"parse_ms": round(parse_ms, 2)},
            )
            if parse_meta.get("fallback_used"):
                self.audit_logger.log_event(
                    "parser_fallback_used",
                    job_id=job_id,
                    mode="ingestion",
                    quality={
                        "file": str(path),
                        "strategy": parse_meta.get(
                            "parser_strategy",
                            "llamaparse",
                        ),
                        "parser_used": parse_meta.get("parser_used"),
                        "fallback_from": parse_meta.get("fallback_from"),
                    },
                    error={
                        "code": str(parse_meta.get("fallback_error_code", "PARSER_FALLBACK")),
                        "message": str(parse_meta.get("fallback_error", "fallback engaged")),
                    },
                )

            chunk_t0 = perf_counter()
            doc_type = path.suffix.lower().lstrip(".") or "unknown"
            chunks = chunk_blocks(
                parsed.blocks,
                doc_type=doc_type,
                max_chars=chunk_size,
                overlap=chunk_overlap,
                enable_hierarchy=enable_hierarchy,
                chunking_mode=chunking_mode,
            )
            chunk_ms = (perf_counter() - chunk_t0) * 1000

            ingest_timestamp = utc_now_iso()
            source_hash = self._file_sha256(path)
            for chunk in chunks:
                meta = chunk.metadata
                meta.source_path = str(path.resolve())
                meta.source_hash = source_hash
                meta.ingest_timestamp_utc = ingest_timestamp
                meta.is_table = meta.chunk_type in {"table", "row"}
                meta.is_image = meta.chunk_type in {"figure", "image_text"}

            return {
                "order_idx": order_idx,
                "file": str(path),
                "path": path,
                "chunks": chunks,
                "parse_ms": parse_ms,
                "chunk_ms": chunk_ms,
            }

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(_parse_one, idx, file_path): (idx, file_path)
                for idx, file_path in enumerate(files)
            }
            for future in as_completed(future_map):
                idx, file_path = future_map[future]
                processed_files += 1
                try:
                    result = future.result()
                    parse_total_ms += float(result["parse_ms"])
                    chunk_total_ms += float(result["chunk_ms"])
                    file_chunks = result["chunks"]
                    files_indexed += 1
                    chunks_indexed += len(file_chunks)
                    parsed_outputs.append(result)
                    file_statuses.append(
                        {
                            "file": str(file_path),
                            "status": "indexed",
                            "chunks": len(file_chunks),
                        }
                    )
                except LlamaParseError as exc:
                    errors.append(
                        {
                            "file": str(file_path),
                            "error": str(exc),
                            "error_code": LlamaParseError.code,
                        }
                    )
                    file_statuses.append(
                        {
                            "file": str(file_path),
                            "status": "failed",
                            "error": str(exc),
                            "error_code": LlamaParseError.code,
                        }
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "file": str(file_path),
                            "error": str(exc),
                            "error_code": "INGESTION_FILE_FAILURE",
                        }
                    )
                    file_statuses.append(
                        {
                            "file": str(file_path),
                            "status": "failed",
                            "error": str(exc),
                            "error_code": "INGESTION_FILE_FAILURE",
                        }
                    )

                if progress_cb:
                    progress_cb(
                        {
                            "files_detected": files_detected,
                            "processed_files": processed_files,
                            "files_indexed": files_indexed,
                            "chunks_indexed": chunks_indexed,
                            "errors": errors,
                            "file_statuses": file_statuses,
                            "timing_ms": {
                                "parse_total": round(parse_total_ms, 2),
                                "chunk_total": round(chunk_total_ms, 2),
                            },
                        }
                    )

        parsed_outputs.sort(key=lambda item: int(item["order_idx"]))
        return {
            "parsed_outputs": parsed_outputs,
            "errors": errors,
            "file_statuses": file_statuses,
            "files_detected": files_detected,
            "processed_files": processed_files,
            "files_indexed": files_indexed,
            "chunks_indexed": chunks_indexed,
            "timing_ms": {
                "parse_total": round(parse_total_ms, 2),
                "chunk_total": round(chunk_total_ms, 2),
            },
        }

    def index_batches(
        self,
        parsed_outputs: list[dict],
        staging: dict,
        progress_cb: Callable[[dict], None] | None = None,
        base_snapshot: dict | None = None,
    ) -> dict:
        staging_bm25 = BM25Index(Path(staging["bm25_dir"]))
        staging_vector = self._build_vector_store(
            persist_directory=str(staging["vector_dir"]),
            mode="ingestion",
        )

        bm25_batch_size = max(1, int(self.settings.bm25_commit_batch_size))
        vector_batch_size = max(1, int(self.settings.vector_upsert_batch_size))
        vector_active = not isinstance(staging_vector, NoOpVectorStore)

        bm25_pending = []
        vector_pending = []
        records: list[dict] = []
        bm25_write_total_ms = 0.0
        embed_total_ms = 0.0
        vector_upsert_total_ms = 0.0
        indexed_chunks = 0
        embedded_chunks = 0

        writer = staging_bm25.open_writer()

        def flush_bm25() -> None:
            nonlocal bm25_write_total_ms
            if not bm25_pending:
                return
            write_t0 = perf_counter()
            staging_bm25.add_documents_to_writer(writer, bm25_pending)
            bm25_write_total_ms += (perf_counter() - write_t0) * 1000
            bm25_pending.clear()

        def flush_vector() -> None:
            nonlocal embed_total_ms, vector_upsert_total_ms, embedded_chunks
            if not vector_pending:
                return
            metrics = staging_vector.upsert_chunk_batch(vector_pending)
            embed_total_ms += float(metrics.get("embed_ms", 0.0))
            vector_upsert_total_ms += float(metrics.get("upsert_ms", 0.0))
            embedded_chunks += int(metrics.get("indexed", 0))
            vector_pending.clear()

        for parsed in parsed_outputs:
            chunks = parsed["chunks"]
            if not chunks:
                continue
            indexed_chunks += len(chunks)
            for chunk in chunks:
                records.append(self._chunk_to_record(chunk))
                bm25_pending.append(chunk)
                if vector_active:
                    vector_pending.append(chunk)
                if len(bm25_pending) >= bm25_batch_size:
                    flush_bm25()
                if vector_active and len(vector_pending) >= vector_batch_size:
                    flush_vector()
            if progress_cb:
                snapshot = dict(base_snapshot or {})
                existing_timing = snapshot.get("timing_ms", {})
                if not isinstance(existing_timing, dict):
                    existing_timing = {}
                snapshot.update(
                    {
                        "chunks_indexed": indexed_chunks,
                        "timing_ms": {
                            **existing_timing,
                            "bm25_write_total": round(bm25_write_total_ms, 2),
                            "embed_total": round(embed_total_ms, 2),
                            "vector_upsert_total": round(vector_upsert_total_ms, 2),
                        },
                    }
                )
                progress_cb(snapshot)

        flush_bm25()
        commit_t0 = perf_counter()
        staging_bm25.commit_writer(writer)
        bm25_write_total_ms += (perf_counter() - commit_t0) * 1000

        if vector_active:
            flush_vector()

        self._write_chunk_catalog(records, Path(staging["chunk_catalog"]))

        # Persist chunks to SQLite
        try:
            # Upsert documents
            doc_map: dict[str, dict] = {}
            for r in records:
                did = r.get("doc_id", "")
                if did and did not in doc_map:
                    doc_map[did] = {
                        "doc_type": r.get("doc_type", ""),
                        "source_path": r.get("source_path"),
                        "source_hash": r.get("source_hash"),
                    }
            for did, info in doc_map.items():
                count = sum(1 for r in records if r.get("doc_id") == did)
                db.upsert_document(did, info["doc_type"], info["source_path"], info["source_hash"], count)
            for r in records:
                r["index_id"] = staging.get("index_id")
            db.insert_chunks(records)
        except Exception:
            pass  # SQLite write failure should not block indexing

        return {
            "records": records,
            "chunks_indexed": indexed_chunks,
            "embedded_chunks": embedded_chunks,
            "timing_ms": {
                "bm25_write_total": round(bm25_write_total_ms, 2),
                "embed_total": round(embed_total_ms, 2),
                "vector_upsert_total": round(vector_upsert_total_ms, 2),
            },
        }

    def finalize_index_swap(self, job_id: str, staging: dict) -> dict:
        swap_t0 = perf_counter()
        if self.settings.index_swap_mode != "atomic_swap":
            self.index_registry.clear_staging()
            return {
                "active_index_id": self._active_index_id,
                "swapped": False,
                "swap_total": round((perf_counter() - swap_t0) * 1000, 2),
            }

        activation = self.index_registry.activate_staging(job_id)
        with self._runtime_lock:
            self._runtime_ready = False
        self.cached_chunks = []
        self._ensure_runtime_initialized()
        swap_ms = round((perf_counter() - swap_t0) * 1000, 2)
        return {
            "active_index_id": activation["active"]["index_id"],
            "previous_index_id": (
                activation["previous_active"].get("index_id")
                if isinstance(activation["previous_active"], dict)
                else None
            ),
            "swapped": True,
            "swap_total": swap_ms,
        }

    def _ingest_files(
        self,
        job_id: str,
        files: list[Path],
        chunk_size: int = 800,
        chunk_overlap: int = 80,
        enable_hierarchy: bool = True,
        chunking_mode: str | None = None,
        progress_cb: Callable[[dict], None] | None = None,
    ) -> dict:
        total_t0 = perf_counter()
        parse_summary = self.parse_chunk_parallel(
            job_id=job_id,
            files=files,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            enable_hierarchy=enable_hierarchy,
            chunking_mode=chunking_mode or str(self.settings.chunking_mode),
            progress_cb=progress_cb,
        )

        staging = self.index_registry.create_staging(job_id)
        index_summary = self.index_batches(
            parse_summary["parsed_outputs"],
            staging,
            progress_cb=progress_cb,
            base_snapshot={
                "files_detected": parse_summary["files_detected"],
                "processed_files": parse_summary["processed_files"],
                "files_indexed": parse_summary["files_indexed"],
                "errors": parse_summary["errors"],
                "file_statuses": parse_summary["file_statuses"],
                "timing_ms": parse_summary["timing_ms"],
            },
        )

        swap_timing = {"swap_total": 0.0}
        active_index_id = self._active_index_id
        swapped = False
        if parse_summary["files_indexed"] > 0:
            swap_summary = self.finalize_index_swap(job_id, staging)
            swap_timing["swap_total"] = float(swap_summary["swap_total"])
            active_index_id = swap_summary.get("active_index_id")
            swapped = bool(swap_summary.get("swapped"))
        else:
            self.index_registry.clear_staging()

        total_ms = round((perf_counter() - total_t0) * 1000, 2)
        timing_ms = {
            "parse_total": parse_summary["timing_ms"]["parse_total"],
            "chunk_total": parse_summary["timing_ms"]["chunk_total"],
            "bm25_write_total": index_summary["timing_ms"]["bm25_write_total"],
            "embed_total": index_summary["timing_ms"]["embed_total"],
            "vector_upsert_total": index_summary["timing_ms"]["vector_upsert_total"],
            "swap_total": round(swap_timing["swap_total"], 2),
            "total": total_ms,
        }
        total_seconds = max(total_ms / 1000.0, 0.001)
        throughput = {
            "chunks_per_sec": round(index_summary["chunks_indexed"] / total_seconds, 2),
            "embeds_per_sec": round(index_summary["embedded_chunks"] / total_seconds, 2),
        }

        self.cached_chunks = self._read_chunk_catalog(self._active_catalog_path())
        return {
            "files_detected": parse_summary["files_detected"],
            "processed_files": parse_summary["processed_files"],
            "files_indexed": parse_summary["files_indexed"],
            "chunks_indexed": index_summary["chunks_indexed"],
            "embedded_chunks": index_summary["embedded_chunks"],
            "errors": parse_summary["errors"],
            "file_statuses": parse_summary["file_statuses"],
            "timing_ms": timing_ms,
            "throughput": throughput,
            "active_index_id": active_index_id,
            "swapped": swapped,
        }

    def ingest_uploads(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 80,
        enable_hierarchy: bool = True,
        chunking_mode: str | None = None,
        files: list[Path] | None = None,
    ) -> dict:
        files = files if files is not None else iter_documents(UPLOAD_DIR)
        return self._ingest_files(
            job_id=f"sync_{uuid.uuid4().hex[:8]}",
            files=files,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            enable_hierarchy=enable_hierarchy,
            chunking_mode=chunking_mode,
        )

    def start_ingestion_job_for_uploads(
        self,
        uploaded_files: list[object],
        chunk_size: int = 800,
        chunk_overlap: int = 80,
        enable_hierarchy: bool = True,
        chunking_mode: str | None = None,
    ) -> dict:
        saved_files = self.save_uploaded_files(uploaded_files)
        if not saved_files:
            return {"saved_files": [], "job_id": None, "status": "no_files"}
        job_id = self.start_ingestion_job(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            enable_hierarchy=enable_hierarchy,
            chunking_mode=chunking_mode,
            files=saved_files,
        )
        job_status = self.get_ingestion_job(job_id) or {}
        return {
            "saved_files": [str(path) for path in saved_files],
            "job_id": job_id,
            "status": str(job_status.get("status", "queued")),
            "error": job_status.get("error"),
            "error_code": job_status.get("error_code"),
            "missing_fields": job_status.get("missing_fields", []),
            "missing_paths": job_status.get("missing_paths", []),
        }

    def _run_ingestion_job(
        self,
        job_id: str,
        files: list[Path],
        chunk_size: int,
        chunk_overlap: int,
        enable_hierarchy: bool,
        chunking_mode: str | None,
    ) -> None:
        try:
            self.audit_logger.log_event(
                "ingestion_job_started",
                job_id=job_id,
                mode="ingestion",
                counts={"files_detected": len(files)},
            )
            self.job_store.update_job(
                job_id,
                {
                    "status": "running",
                    "files_detected": len(files),
                    "processed_files": 0,
                    "files_indexed": 0,
                    "chunks_indexed": 0,
                    "errors": [],
                    "error_code": None,
                    "timing_ms": {
                        "parse_total": 0.0,
                        "chunk_total": 0.0,
                        "bm25_write_total": 0.0,
                        "embed_total": 0.0,
                        "vector_upsert_total": 0.0,
                        "swap_total": 0.0,
                        "total": 0.0,
                    },
                },
            )

            def on_progress(snapshot: dict) -> None:
                snapshot_timing = snapshot.get("timing_ms", {})
                self.job_store.update_job(
                    job_id,
                    {
                        "status": "running",
                        "files_detected": snapshot.get("files_detected", 0),
                        "processed_files": snapshot.get("processed_files", 0),
                        "files_indexed": snapshot.get("files_indexed", 0),
                        "chunks_indexed": snapshot.get("chunks_indexed", 0),
                        "errors": snapshot.get("errors", []),
                        "file_statuses": snapshot.get("file_statuses", []),
                        "timing_ms": snapshot_timing if isinstance(snapshot_timing, dict) else {},
                        "error_code": None,
                    },
                )
                self.audit_logger.log_event(
                    "ingestion_job_progress",
                    job_id=job_id,
                    mode="ingestion",
                    counts={
                        "files_detected": snapshot.get("files_detected", 0),
                        "processed_files": snapshot.get("processed_files", 0),
                        "files_indexed": snapshot.get("files_indexed", 0),
                        "chunks_indexed": snapshot.get("chunks_indexed", 0),
                        "errors_count": len(snapshot.get("errors", [])),
                    },
                    durations_ms=(
                        snapshot_timing if isinstance(snapshot_timing, dict) else {}
                    ),
                )

            summary = self._ingest_files(
                job_id=job_id,
                files=files,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                enable_hierarchy=enable_hierarchy,
                chunking_mode=chunking_mode,
                progress_cb=on_progress,
            )
            self.job_store.update_job(
                job_id,
                {"status": "completed", "error_code": None, **summary},
            )
            self.audit_logger.log_event(
                "ingestion_job_finished",
                job_id=job_id,
                mode="ingestion",
                counts={
                    "files_detected": summary.get("files_detected", 0),
                    "files_indexed": summary.get("files_indexed", 0),
                    "chunks_indexed": summary.get("chunks_indexed", 0),
                    "errors_count": len(summary.get("errors", [])),
                },
                durations_ms=summary.get("timing_ms", {}),
                quality={
                    "throughput": summary.get("throughput", {}),
                    "swapped": summary.get("swapped", False),
                    "active_index_id": summary.get("active_index_id"),
                },
                error=None,
            )
        except Exception as exc:
            self.job_store.update_job(
                job_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "error_code": "INGESTION_JOB_FAILURE",
                },
            )
            self.audit_logger.log_event(
                "ingestion_failed",
                job_id=job_id,
                mode="ingestion",
                error={"code": "INGESTION_JOB_FAILURE", "message": str(exc)},
            )

    def start_ingestion_job(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 80,
        enable_hierarchy: bool = True,
        chunking_mode: str | None = None,
        files: list[Path] | None = None,
    ) -> str:
        files = files if files is not None else iter_documents(UPLOAD_DIR)
        job_id = self.job_store.create_job(
            {
                "status": "queued",
                "files_detected": len(files),
                "processed_files": 0,
                "files_indexed": 0,
                "chunks_indexed": 0,
                "errors": [],
                "error_code": None,
                "queued_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        thread = threading.Thread(
            target=self._run_ingestion_job,
            args=(job_id, files, chunk_size, chunk_overlap, enable_hierarchy, chunking_mode),
            daemon=True,
        )
        with self._thread_lock:
            self._job_threads[job_id] = thread
        thread.start()
        return job_id

    def get_ingestion_job(self, job_id: str) -> dict | None:
        return self.job_store.get_job(job_id)

    def list_ingestion_jobs(self) -> list[dict]:
        return self.job_store.list_jobs()

    def has_ready_index(self) -> bool:
        return len(self.saved_chunks()) > 0

    def query_fast(self, question: str, filters: dict | None = None, mode: str = "default") -> dict:
        self._ensure_runtime_initialized()
        assert self.executor is not None
        assert self.rewriter is not None
        assert self.planner is not None

        request_id = new_request_id()
        total_t0 = perf_counter()
        normalized_mode = mode if mode in {"default", "deep"} else "default"
        question_hash = hash_query(question)
        feature_flags = {
            "reranker_enabled": bool(self.settings.reranker_enabled),
            "hyde_enabled": bool(self.settings.hyde_enabled),
            "decomposition_enabled": bool(self.settings.decomposition_enabled),
            "deep_rewrite_enabled": bool(self.settings.deep_rewrite_enabled),
        }
        normalized_filters = self._normalize_filters(filters)

        self.audit_logger.log_event(
            "query_started",
            request_id=request_id,
            mode=normalized_mode,
            query_text_hash=question_hash,
            filters=normalized_filters or {},
            feature_flags=feature_flags,
        )

        rewrite_t0 = perf_counter()
        rewritten_query = question
        answer_id = None
        answer_path = None
        try:
            self.planner.set_deep_features(
                enable_hyde=feature_flags["hyde_enabled"],
                enable_decomposition=feature_flags["decomposition_enabled"],
            )
            rewritten_query = self.rewriter.rewrite(
                question,
                self.memory,
                mode=normalized_mode,
                deep_enabled=feature_flags["deep_rewrite_enabled"],
            )
            rewrite_ms = (perf_counter() - rewrite_t0) * 1000

            exec_result = self.executor.run(
                rewritten_query,
                filters=normalized_filters,
                mode=normalized_mode,
            )
            llm_payload = exec_result.llm_payload
            validation = exec_result.validation

            self.memory.add_user_message(question)
            self.memory.add_ai_message(llm_payload.get("answer", ""))

            ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
            answer_id = uuid.uuid4().hex[:8]
            answer_path = ANSWERS_DIR / f"answer_{answer_id}.json"
            answer_path.write_text(json.dumps(llm_payload, indent=2), encoding="utf-8")

            # Also save detailed logs
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            log_path = LOGS_DIR / f"log_{answer_id}.json"
            retrieval_ids = [r.get("chunk_id") for r in exec_result.results if r.get("chunk_id")]
            provenance = llm_payload.get("provenance", []) or []
            citation_hit = bool(provenance) and all(cid in retrieval_ids for cid in provenance)
            timing_ms = {
                "rewrite_ms": round(rewrite_ms, 2),
                "plan_ms": round(exec_result.plan_ms, 2),
                "retrieval_ms": round(exec_result.retrieval_ms, 2),
                "llm_ms": round(exec_result.llm_ms, 2),
                "validation_ms": round(exec_result.validation_ms, 2),
                "total_ms": round((perf_counter() - total_t0) * 1000, 2),
            }
            quality = {
                "retrieval_count": len(exec_result.results),
                "provenance_count": len(provenance),
                "validation_valid": bool(validation.get("valid", False)),
                "validation_issues": validation.get("issues", []),
                "citation_hit": citation_hit,
            }
            log_data = {
                "request_id": request_id,
                "original_question": question,
                "question_hash": question_hash,
                "rewritten_question": rewritten_query,
                "mode": normalized_mode,
                "filters": normalized_filters,
                "plan": [
                    {"tool": s.tool, "k": s.k, "note": s.note}
                    for s in exec_result.plan.steps
                ],
                "intent": exec_result.plan.intent,
                "execution_log": exec_result.log,
                "validation": validation,
                "feature_flags": feature_flags,
                "timing_ms": timing_ms,
                "quality": quality,
            }
            log_path.write_text(json.dumps(log_data, indent=2), encoding="utf-8")

            # Save to SQLite
            db.save_answer(request_id, llm_payload)
            db.save_query_log(request_id, log_data)

            self.audit_logger.log_event(
                "retrieval_finished",
                request_id=request_id,
                mode=normalized_mode,
                durations_ms={
                    "plan_ms": round(exec_result.plan_ms, 2),
                    "retrieval_ms": round(exec_result.retrieval_ms, 2),
                },
                counts={"retrieval_count": len(exec_result.results)},
            )
            self.audit_logger.log_event(
                "llm_finished",
                request_id=request_id,
                mode=normalized_mode,
                durations_ms={"llm_ms": round(exec_result.llm_ms, 2)},
                counts={"provenance_count": len(provenance)},
                feature_flags=feature_flags,
            )
            if exec_result.error:
                self.audit_logger.log_event(
                    "error",
                    request_id=request_id,
                    mode=normalized_mode,
                    query_text_hash=question_hash,
                    error=exec_result.error,
                )
                if (
                    str(exec_result.error.get("code", "")) == "SUMMARY_PROVENANCE_MISSING"
                    and getattr(exec_result.plan, "intent", "") == "summarization"
                ):
                    self.audit_logger.log_event(
                        "summary_provenance_missing",
                        request_id=request_id,
                        mode=normalized_mode,
                        error=exec_result.error,
                    )
            self.audit_logger.log_event(
                "validation_finished",
                request_id=request_id,
                mode=normalized_mode,
                durations_ms={"validation_ms": round(exec_result.validation_ms, 2)},
                quality=quality,
                feature_flags=feature_flags,
            )
            self.audit_logger.log_event(
                "query_finished",
                request_id=request_id,
                mode=normalized_mode,
                query_text_hash=question_hash,
                durations_ms=timing_ms,
                counts={"retrieval_count": len(exec_result.results)},
                quality=quality,
                feature_flags=feature_flags,
                error=None,
            )

            return {
                "request_id": request_id,
                "rewritten_query": rewritten_query,
                "plan": exec_result.plan,
                "retrieval": exec_result.results,
                "llm": llm_payload,
                "validation": validation,
                "quality": quality,
                "feature_flags": feature_flags,
                "error": exec_result.error,
                "timing_ms": timing_ms,
                "log": exec_result.log,
                "answer_path": str(answer_path) if answer_path else None,
                # Backward-compatible alias.
                "latency_ms": {
                    "retrieval_ms": timing_ms["retrieval_ms"],
                    "llm_ms": timing_ms["llm_ms"],
                    "total_ms": timing_ms["total_ms"],
                },
            }
        except Exception as exc:
            self.audit_logger.log_event(
                "error",
                request_id=request_id,
                mode=normalized_mode,
                query_text_hash=question_hash,
                error={"code": "QUERY_FAILURE", "message": str(exc)},
            )
            raise

    def query(self, question: str, filters: dict | None = None) -> dict:
        return self.query_fast(question=question, filters=filters, mode="default")

    def saved_chunks(self) -> list[dict]:
        if not self.cached_chunks:
            # Try SQLite first, fall back to JSONL catalog
            try:
                rows = db.get_all_chunks()
                if rows:
                    self.cached_chunks = rows
                    return self.cached_chunks
            except Exception:
                pass
            self.cached_chunks = self._read_chunk_catalog(self._active_catalog_path())
        return self.cached_chunks

    def list_documents(self) -> list[str]:
        try:
            docs = db.list_documents()
            if docs:
                return [d["doc_id"] for d in docs]
        except Exception:
            pass
        return sorted({c.get("doc_id") for c in self.saved_chunks() if c.get("doc_id")})

    def delete_document(self, doc_id: str) -> dict:
        """Remove a document and its chunks from all indices."""
        self._ensure_runtime_initialized()

        # 1. Remove from SQLite
        removed_count = db.delete_document(doc_id)

        # 2. Also remove from JSONL catalog (keep in sync during transition)
        catalog_path = self._active_catalog_path()
        all_chunks = self._read_chunk_catalog(catalog_path)
        remaining = [c for c in all_chunks if c.get("doc_id") != doc_id]
        if len(remaining) < len(all_chunks):
            self._write_chunk_catalog(remaining, catalog_path)

        self.cached_chunks = []  # Invalidate cache

        if removed_count == 0:
            return {"deleted": False, "doc_id": doc_id, "error": "Document not found"}

        # 3. Remove from BM25 index
        bm25_deleted = 0
        if self.bm25:
            bm25_deleted = self.bm25.delete_by_doc_id(doc_id)

        # 4. Remove from vector store
        vector_deleted = 0
        if self.vector and not isinstance(self.vector, NoOpVectorStore):
            vector_deleted = self.vector.delete_by_doc_id(doc_id)

        # 5. Remove uploaded file
        upload_path = UPLOAD_DIR / doc_id
        if upload_path.exists():
            upload_path.unlink()

        self.audit_logger.log_event(
            "document_deleted",
            doc_id=doc_id,
            chunks_removed=removed_count,
            bm25_deleted=bm25_deleted,
            vector_deleted=vector_deleted,
        )
        db.log_audit_event(
            "document_deleted",
            doc_id=doc_id,
            chunks_removed=removed_count,
        )

        return {
            "deleted": True,
            "doc_id": doc_id,
            "chunks_removed": removed_count,
            "bm25_deleted": bm25_deleted,
            "vector_deleted": vector_deleted,
        }

    def _normalize_filters(self, filters: dict | None) -> dict | None:
        if not filters:
            return filters
        normalized = dict(filters)
        known_docs = self.list_documents()
        doc_lookup = {doc.casefold(): doc for doc in known_docs}

        # Frontend sends "document" key — normalize to "doc_id"
        if "document" in normalized and "doc_id" not in normalized:
            normalized["doc_id"] = normalized.pop("document")

        doc_id = normalized.get("doc_id")
        if doc_id:
            normalized["doc_id"] = doc_lookup.get(str(doc_id).casefold(), str(doc_id))

        doc_ids = normalized.get("doc_ids")
        if isinstance(doc_ids, list):
            resolved: list[str] = []
            for item in doc_ids:
                key = str(item).casefold()
                resolved.append(doc_lookup.get(key, str(item)))
            normalized["doc_ids"] = resolved
            if len(resolved) == 1 and not normalized.get("doc_id"):
                normalized["doc_id"] = resolved[0]

        return normalized

    def get_retriever_weights(self) -> tuple[float, float]:
        self._ensure_runtime_initialized()
        if not self.hybrid:
            return 1.0, 0.0
        if isinstance(self.vector, NoOpVectorStore):
            return 1.0, 0.0
        return self.hybrid.weight_bm25, self.hybrid.weight_vector

    def update_retriever_weights(self, bm25_weight: float, vector_weight: float):
        self._ensure_runtime_initialized()
        if self.hybrid:
            if isinstance(self.vector, NoOpVectorStore):
                self.hybrid.weight_bm25 = 1.0
                self.hybrid.weight_vector = 0.0
                return
            self.hybrid.weight_bm25 = bm25_weight
            self.hybrid.weight_vector = vector_weight

    def set_reranker_enabled(self, enabled: bool) -> None:
        self._ensure_runtime_initialized()
        self.settings.reranker_enabled = enabled
        if self.hybrid:
            self.hybrid.set_reranker_enabled(enabled)

    def set_vector_enabled(self, enabled: bool) -> None:
        enabled_bool = bool(enabled)
        if bool(self.settings.vector_enabled) == enabled_bool:
            return
        self.settings.vector_enabled = enabled_bool
        self.audit_logger.log_event(
            "vector_backend_toggle",
            mode="runtime",
            quality={"vector_enabled": enabled_bool},
        )
        with self._runtime_lock:
            self._runtime_ready = False

    def is_vector_available(self) -> bool:
        self._ensure_runtime_initialized()
        return not isinstance(self.vector, NoOpVectorStore)

    def set_hyde_enabled(self, enabled: bool) -> None:
        self._ensure_runtime_initialized()
        self.settings.hyde_enabled = enabled
        if self.planner:
            self.planner.set_deep_features(
                enable_hyde=enabled,
                enable_decomposition=self.settings.decomposition_enabled,
            )

    def set_decomposition_enabled(self, enabled: bool) -> None:
        self._ensure_runtime_initialized()
        self.settings.decomposition_enabled = enabled
        if self.planner:
            self.planner.set_deep_features(
                enable_hyde=self.settings.hyde_enabled,
                enable_decomposition=enabled,
            )

    def set_deep_rewrite_enabled(self, enabled: bool) -> None:
        self.settings.deep_rewrite_enabled = enabled

    def get_ingestion_tuning(self) -> dict:
        return {
            "ingestion_parse_workers": int(self.settings.ingestion_parse_workers),
            "ingestion_parse_queue_size": int(self.settings.ingestion_parse_queue_size),
            "embedding_batch_size": int(self.settings.embedding_batch_size),
            "vector_upsert_batch_size": int(self.settings.vector_upsert_batch_size),
            "bm25_commit_batch_size": int(self.settings.bm25_commit_batch_size),
            "chunking_mode": str(self.settings.chunking_mode),
            "index_swap_mode": str(self.settings.index_swap_mode),
        }

    def set_ingestion_tuning(
        self,
        ingestion_parse_workers: int,
        ingestion_parse_queue_size: int,
        embedding_batch_size: int,
        vector_upsert_batch_size: int,
        bm25_commit_batch_size: int,
        chunking_mode: str,
        index_swap_mode: str,
    ) -> dict:
        self.settings.ingestion_parse_workers = max(1, min(int(ingestion_parse_workers), 16))
        self.settings.ingestion_parse_queue_size = max(
            1, min(int(ingestion_parse_queue_size), 1024)
        )
        self.settings.embedding_batch_size = max(1, min(int(embedding_batch_size), 256))
        self.settings.vector_upsert_batch_size = max(1, min(int(vector_upsert_batch_size), 2048))
        self.settings.bm25_commit_batch_size = max(1, min(int(bm25_commit_batch_size), 8192))
        self.settings.chunking_mode = (
            "semantic_hybrid" if str(chunking_mode) == "semantic_hybrid" else "window"
        )
        self.settings.index_swap_mode = "atomic_swap"
        return self.get_ingestion_tuning()

    def reset_ingestion_tuning_defaults(self) -> dict:
        return self.set_ingestion_tuning(
            ingestion_parse_workers=4,
            ingestion_parse_queue_size=32,
            embedding_batch_size=32,
            vector_upsert_batch_size=64,
            bm25_commit_batch_size=256,
            chunking_mode="window",
            index_swap_mode="atomic_swap",
        )

    def get_index_registry_status(self) -> dict:
        active = self.index_registry.get_active()
        staging = self.index_registry.get_staging()
        integrity = self._inspect_index_payload(active)
        return {
            "active": active,
            "staging": staging,
            "swap_mode": self.settings.index_swap_mode,
            "runtime_active_index_id": self._active_index_id,
            "integrity": integrity,
            "vector_enabled": bool(self.settings.vector_enabled),
            "vector_available": self.is_vector_available(),
            "vector_reason": (
                self.vector.reason if isinstance(self.vector, NoOpVectorStore) else None
            ),
        }

    def switch_to_latest_clean_index(self) -> dict:
        latest_clean = self._find_latest_clean_index_payload()
        active = self.index_registry.get_active()
        if not latest_clean:
            return {
                "switched": False,
                "active_index_id": active.get("index_id"),
                "error": {
                    "code": "NO_CLEAN_INDEX_AVAILABLE",
                    "message": "No clean non-demo index was found.",
                },
            }
        if latest_clean.get("index_id") == active.get("index_id"):
            return {
                "switched": False,
                "active_index_id": active.get("index_id"),
                "message": "Active index is already clean.",
            }
        switched = self.index_registry.set_active(latest_clean)
        self.audit_logger.log_event(
            "index_auto_switched",
            mode="runtime",
            quality={
                "from_index_id": active.get("index_id"),
                "to_index_id": switched["active"]["index_id"],
                "reason": "admin_switch_to_latest_clean_index",
            },
        )
        with self._runtime_lock:
            self._runtime_ready = False
        self.cached_chunks = []
        self._ensure_runtime_initialized()
        return {
            "switched": True,
            "active_index_id": switched["active"]["index_id"],
            "previous_index_id": (
                switched["previous_active"].get("index_id")
                if isinstance(switched.get("previous_active"), dict)
                else None
            ),
        }


def load_pipeline(lazy_init: bool = True) -> Pipeline:
    return Pipeline(lazy_init=lazy_init)
