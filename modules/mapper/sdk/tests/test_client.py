"""
Tests for pdf_autofiller_mapper.client — PDFMapperClient.

httpx transport is mocked via httpx.MockTransport so no real server needed.
"""

import pytest
import httpx
from unittest.mock import MagicMock, patch

from pdf_autofiller_mapper.client import PDFMapperClient
from pdf_autofiller_mapper.exceptions import (
    PDFMapperError,
    APIError,
    ConnectionError,
    TimeoutError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(base_url="http://test-server:8000", api_key=None):
    return PDFMapperClient(base_url=base_url, api_key=api_key)


def _mock_transport(status_code=200, json_body=None):
    """Return an httpx transport that always responds with given status/body."""
    body = json_body or {"status": "ok"}
    import json

    def handler(request):
        return httpx.Response(status_code, json=body)

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestPDFMapperClientInit:
    def test_base_url_stripped(self):
        client = PDFMapperClient(base_url="http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"

    def test_api_key_stored(self):
        client = PDFMapperClient(api_key="my-key")
        assert client.api_key == "my-key"

    def test_no_api_key_ok(self):
        client = PDFMapperClient()
        assert client.api_key is None

    def test_mapper_resource_attached(self):
        from pdf_autofiller_mapper.resources.mapper import MapperResource
        client = PDFMapperClient()
        assert isinstance(client.mapper, MapperResource)

    def test_context_manager(self):
        with PDFMapperClient() as client:
            assert client is not None


# ---------------------------------------------------------------------------
# Successful requests
# ---------------------------------------------------------------------------

class TestPDFMapperClientRequest:
    def test_health_check_success(self):
        transport = _mock_transport(200, {"status": "ok"})
        client = PDFMapperClient(transport=transport)
        result = client.health_check()
        assert result["status"] == "ok"

    def test_api_key_sent_in_header(self):
        received_headers = {}

        def handler(request):
            received_headers.update(dict(request.headers))
            return httpx.Response(200, json={"status": "ok"})

        client = PDFMapperClient(api_key="secret-key", transport=httpx.MockTransport(handler))
        client.health_check()
        assert received_headers.get("x-api-key") == "secret-key"

    def test_no_api_key_header_absent(self):
        received_headers = {}

        def handler(request):
            received_headers.update(dict(request.headers))
            return httpx.Response(200, json={"status": "ok"})

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        client.health_check()
        assert "x-api-key" not in received_headers


# ---------------------------------------------------------------------------
# Error translation
# ---------------------------------------------------------------------------

class TestPDFMapperClientErrors:
    def test_404_raises_api_error(self):
        transport = _mock_transport(404, {"detail": "not found"})
        client = PDFMapperClient(transport=transport)
        with pytest.raises(APIError) as exc_info:
            client.health_check()
        assert exc_info.value.status_code == 404

    def test_500_raises_api_error(self):
        transport = _mock_transport(500, {"detail": "internal error"})
        client = PDFMapperClient(transport=transport)
        with pytest.raises(APIError) as exc_info:
            client.health_check()
        assert exc_info.value.status_code == 500

    def test_api_error_is_pdf_mapper_error(self):
        transport = _mock_transport(400, {})
        client = PDFMapperClient(transport=transport)
        with pytest.raises(PDFMapperError):
            client.health_check()

    def test_connect_error_raises_connection_error(self):
        def handler(request):
            raise httpx.ConnectError("refused")

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        with pytest.raises(ConnectionError):
            client.health_check()

    def test_timeout_raises_timeout_error(self):
        def handler(request):
            raise httpx.ReadTimeout("timed out", request=request)

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        with pytest.raises(TimeoutError):
            client.health_check()

    def test_connection_error_is_pdf_mapper_error(self):
        def handler(request):
            raise httpx.ConnectError("refused")

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        with pytest.raises(PDFMapperError):
            client.health_check()


# ---------------------------------------------------------------------------
# MapperResource — spot-check one method to confirm routing
# ---------------------------------------------------------------------------

class TestMapperResource:
    def test_make_embed_file_posts_to_correct_path(self):
        captured = {}

        def handler(request):
            captured["path"] = request.url.path
            captured["method"] = request.method
            return httpx.Response(200, json={"status": "ok"})

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        client.mapper.make_embed_file(pdf_path="s3://bucket/form.pdf")
        assert captured["path"] == "/make-embed-file"
        assert captured["method"] == "POST"

    def test_health_check_posts_to_health(self):
        captured = {}

        def handler(request):
            captured["path"] = request.url.path
            return httpx.Response(200, json={"status": "ok"})

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        client.health_check()
        assert captured["path"] == "/health"
