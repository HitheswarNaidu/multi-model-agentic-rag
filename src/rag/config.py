from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = Field("")
    embedding_model: str = Field("all-mpnet-base-v2")
    vector_enabled: bool = Field(False)
    streamlit_port: int = Field(8501)
    fast_path_enabled: bool = Field(True)
    reranker_enabled: bool = Field(False)
    hyde_enabled: bool = Field(False)
    deep_rewrite_enabled: bool = Field(False)
    decomposition_enabled: bool = Field(False)
    expert_mode_default: bool = Field(False)

    # Strict Docling OCR configuration.
    docling_ocr_force: bool = Field(False)
    docling_ocr_det_model_path: str = Field("")
    docling_ocr_cls_model_path: str = Field("")
    docling_ocr_rec_model_path: str = Field("")
    docling_ocr_rec_keys_path: str = Field("")
    docling_ocr_font_path: str = Field("")
    docling_ocr_auto: bool = Field(True)
    pdf_parse_strategy: str = Field("fast_text_first")
    pdf_text_min_chars: int = Field(300)
    chunking_mode: str = Field("window")
    ignore_test_demo_indexes: bool = Field(True)
    demo_index_markers: list[str] = Field(
        default_factory=lambda: ["doc1", "Apple revenue is $100."]
    )

    ingestion_parse_workers: int = Field(4)
    ingestion_parse_queue_size: int = Field(32)
    embedding_batch_size: int = Field(32)
    vector_upsert_batch_size: int = Field(64)
    bm25_commit_batch_size: int = Field(256)
    index_swap_mode: str = Field("atomic_swap")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
