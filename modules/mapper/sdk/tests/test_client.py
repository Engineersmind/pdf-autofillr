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
            import json as _json
            captured["path"] = request.url.path
            captured["method"] = request.method
            captured["body"] = _json.loads(request.content)
            return httpx.Response(200, json={"status": "ok"})

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        client.mapper.make_embed_file(user_id="1", session_id="1", pdf_doc_id="100")
        assert captured["path"] == "/mapper/make-embed-file"
        assert captured["method"] == "POST"
        assert captured["body"]["user_id"] == "1"
        assert captured["body"]["session_id"] == "1"
        assert captured["body"]["pdf_doc_id"] == "100"

    def test_fill_posts_to_correct_path(self):
        captured = {}

        def handler(request):
            import json as _json
            captured["path"] = request.url.path
            captured["body"] = _json.loads(request.content)
            return httpx.Response(200, json={"status": "ok"})

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        client.mapper.fill(user_id="1", session_id="1", pdf_doc_id="100")
        assert captured["path"] == "/mapper/fill"
        assert captured["body"]["user_id"] == "1"

    def test_check_embed_file_posts_to_correct_path(self):
        captured = {}

        def handler(request):
            captured["path"] = request.url.path
            return httpx.Response(200, json={"status": "ok"})

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        client.mapper.check_embed_file(user_id="1", session_id="1", pdf_doc_id="100")
        assert captured["path"] == "/mapper/check-embed-file"

    def test_run_all_posts_to_correct_path(self):
        captured = {}

        def handler(request):
            captured["path"] = request.url.path
            return httpx.Response(200, json={"status": "ok"})

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        client.mapper.run_all(user_id="1", session_id="1", pdf_doc_id="100")
        assert captured["path"] == "/mapper/run-all"

    def test_extract_posts_to_correct_path(self):
        captured = {}

        def handler(request):
            import json as _json
            captured["path"] = request.url.path
            captured["body"] = _json.loads(request.content)
            return httpx.Response(200, json={"status": "ok"})

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        client.mapper.extract(pdf_path="/data/input/form.pdf", user_id="1", session_id="1", pdf_doc_id="100")
        assert captured["path"] == "/mapper/extract"
        assert captured["body"]["pdf_path"] == "/data/input/form.pdf"

    def test_upload_file_posts_to_correct_path(self, tmp_path):
        captured = {}

        def handler(request):
            captured["path"] = request.url.path
            captured["method"] = request.method
            return httpx.Response(200, json={"status": "success", "path": "/app/data/input/1/1/100/input.pdf", "size_bytes": 8})

        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        result = client.mapper.upload_file(
            user_id="1", session_id="1", pdf_doc_id="100",
            filename="input.pdf",
            source=str(pdf),
        )
        assert captured["path"] == "/upload/1/1/100/input.pdf"
        assert captured["method"] == "POST"
        assert result["status"] == "success"

    def test_upload_file_accepts_bytes(self):
        captured = {}

        def handler(request):
            captured["path"] = request.url.path
            return httpx.Response(200, json={"status": "success", "size_bytes": 2})

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        client.mapper.upload_file(
            user_id="1", session_id="1", pdf_doc_id="100",
            filename="global_schema.json",
            source=b"{}",
        )
        assert captured["path"] == "/upload/1/1/100/global_schema.json"

    def test_upload_file_rejects_invalid_filename(self):
        client = PDFMapperClient()
        with pytest.raises(ValueError, match="filename must be one of"):
            client.mapper.upload_file("1", "1", "100", "evil.exe", b"data")

    def test_health_check_posts_to_health(self):
        captured = {}

        def handler(request):
            captured["path"] = request.url.path
            return httpx.Response(200, json={"status": "ok"})

        client = PDFMapperClient(transport=httpx.MockTransport(handler))
        client.health_check()
        assert captured["path"] == "/health"
