"""Basic tests for the PDF Autofiller Python SDK."""

import pytest
from pdf_autofiller import PDFMapperClient


def test_client_instantiation():
    client = PDFMapperClient(api_key="test-key", base_url="http://localhost:8000")
    assert client is not None


def test_client_requires_api_key():
    with pytest.raises((TypeError, ValueError)):
        PDFMapperClient()
