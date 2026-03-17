"""
End-to-end tests using the PDF Autofiller Mapper SDK.

Requires:
    pip install pdf-autofiller-mapper[embedded]
    Java 17+ on PATH
    modules/mapper/config.ini configured

Run:
    pytest tests/e2e/ -v
"""

import pytest


# ---------------------------------------------------------------------------
# Placeholder tests — implement when e2e test suite is started
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="e2e tests not yet implemented")
def test_embedded_two_phase():
    """PDFMapper: make_embed_file then fill produces a valid PDF."""
    pass


@pytest.mark.skip(reason="e2e tests not yet implemented")
def test_http_client_two_phase():
    """PDFMapperClient: make_embed_file then fill via HTTP."""
    pass
