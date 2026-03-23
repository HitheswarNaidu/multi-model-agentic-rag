from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Parsing (LlamaParse)
    llama_cloud_api_key: str = Field("")

    # Embeddings (NVIDIA)
    nvidia_api_key: str = Field("")
    embedding_model: str = Field("nvidia/llama-nemotron-embed-1b-v2")
    vector_enabled: bool = Field(True)

    # LLM (Groq primary + OpenRouter fallback)
    groq_api_key: str = Field("")
    openrouter_api_key: str = Field("")
    llm_fallback_chain: str = Field(
        "groq:openai/gpt-oss-120b,groq:openai/gpt-oss-20b,"
        "groq:llama-3.3-70b-versatile,groq:llama-3.1-8b-instant,"
        "openrouter:openrouter/free"
    )

    # Advanced RAG features (all ON by default)
    reranker_enabled: bool = Field(True)
    hyde_enabled: bool = Field(True)
    deep_rewrite_enabled: bool = Field(True)
    decomposition_enabled: bool = Field(True)
    expert_mode_default: bool = Field(False)

    # Chunking
    chunking_mode: str = Field("semantic_hybrid")

    # Index management
    ignore_test_demo_indexes: bool = Field(True)
    demo_index_markers: list[str] = Field(
        default_factory=lambda: ["doc1", "Apple revenue is $100."]
    )

    # Ingestion tuning
    ingestion_parse_workers: int = Field(4)
    ingestion_parse_queue_size: int = Field(32)
    embedding_batch_size: int = Field(32)
    vector_upsert_batch_size: int = Field(64)
    bm25_commit_batch_size: int = Field(256)
    index_swap_mode: str = Field("atomic_swap")

    # Streamlit
    streamlit_port: int = Field(8501)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
