import streamlit as st
from functools import lru_cache
from rag.pipeline import load_pipeline, Pipeline


@lru_cache(maxsize=1)
def get_pipeline() -> Pipeline:
    return load_pipeline()


def reset_pipeline():
    get_pipeline.cache_clear()


def get_state(name: str, default=None):
    if name not in st.session_state:
        st.session_state[name] = default
    return st.session_state[name]


def set_state(name: str, value):
    st.session_state[name] = value
