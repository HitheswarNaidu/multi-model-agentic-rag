from rag.config import Settings


def test_new_api_key_fields():
    s = Settings(
        llama_cloud_api_key="llx-test",
        nvidia_api_key="nvapi-test",
        groq_api_key="gsk_test",
        openrouter_api_key="sk-or-test",
    )
    assert s.llama_cloud_api_key == "llx-test"
    assert s.nvidia_api_key == "nvapi-test"
    assert s.groq_api_key == "gsk_test"
    assert s.openrouter_api_key == "sk-or-test"


def test_new_defaults():
    s = Settings(
        vector_enabled=True,
        embedding_model="nvidia/llama-nemotron-embed-1b-v2",
    )
    assert s.vector_enabled is True
    assert s.hyde_enabled is True
    assert s.deep_rewrite_enabled is True
    assert s.decomposition_enabled is True
    assert s.reranker_enabled is True
    assert s.embedding_model == "nvidia/llama-nemotron-embed-1b-v2"


def test_llm_fallback_chain_default():
    s = Settings(_env_file=None)
    assert s.llm_fallback_chain == (
        "groq:openai/gpt-oss-120b,groq:openai/gpt-oss-20b,"
        "groq:llama-3.3-70b-versatile,groq:llama-3.1-8b-instant,"
        "openrouter:openrouter/free"
    )


def test_removed_fields_absent():
    s = Settings()
    assert not hasattr(s, "gemini_api_key")
    assert not hasattr(s, "docling_ocr_force")
    assert not hasattr(s, "fast_path_enabled")
    assert not hasattr(s, "pdf_parse_strategy")
