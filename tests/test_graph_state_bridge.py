"""Legacy Streamlit session state test — skipped since frontend moved to Next.js."""

import pytest

pytest.skip(
    "Streamlit session state tests are legacy; frontend is now Next.js",
    allow_module_level=True,
)
