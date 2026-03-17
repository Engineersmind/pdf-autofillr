"""
Integration tests for the mapper HTTP API.

These tests require a running server:
    cd modules/mapper && python api_server.py

Run:
    pytest tests/integration/ -v
"""

import pytest

SERVER = "http://localhost:8000"
PDF_TEMPLATE = "data/modules/mapper_sample/input/small_4page.pdf"
SCHEMA_KEYS = "data/modules/mapper_sample/form_keys_flat.json"


# ---------------------------------------------------------------------------
# Placeholder tests — implement when integration test suite is started
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="integration tests not yet implemented")
def test_health():
    """GET /health returns status ok."""
    pass


@pytest.mark.skip(reason="integration tests not yet implemented")
def test_extract():
    """POST /extract returns field list from a real PDF."""
    pass


@pytest.mark.skip(reason="integration tests not yet implemented")
def test_make_embed_file():
    """POST /make-embed-file produces an embedded PDF."""
    pass


@pytest.mark.skip(reason="integration tests not yet implemented")
def test_fill():
    """POST /fill fills an embedded PDF with user data."""
    pass


@pytest.mark.skip(reason="integration tests not yet implemented")
def test_run_all():
    """POST /run-all runs the full pipeline end-to-end."""
    pass
