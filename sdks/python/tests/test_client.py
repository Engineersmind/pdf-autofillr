"""Tests for MapperClient."""

import json
import pytest
import httpx
from unittest.mock import MagicMock, patch

from pdf_autofiller import MapperClient
from pdf_autofiller.exceptions import (
    APIError,
    AuthenticationError,
    TimeoutError,
    ValidationError,
)

FUNCTION_URL = "https://fake.lambda-url.us-east-1.on.aws/"
API_KEY = "test-key-123"

# Helper so tests always hit the fake URL, not the baked-in default
def _client(**kwargs):
    return MapperClient(api_key=API_KEY, function_url=FUNCTION_URL, **kwargs)


def _make_response(result: dict, status_code: int = 200) -> MagicMock:
    """Build a fake httpx.Response with the Lambda's response shape."""
    body = json.dumps({
        "message": "Processing completed successfully",
        "operation": "test",
        "result": result,
        "request_processing_time_seconds": 1.23,
    })
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.json.return_value = {"statusCode": status_code, "body": body}
    return mock


def _make_error_response(status_code: int, message: str, error: str = "Error") -> MagicMock:
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.json.return_value = {"error": error, "message": message}
    return mock


class TestMapperClientInit:
    def test_requires_api_key(self):
        with pytest.raises(ValidationError):
            MapperClient(api_key="")

    def test_requires_url_when_no_default(self):
        import pdf_autofiller.client as _mod
        original = _mod._DEFAULT_FUNCTION_URL
        try:
            _mod._DEFAULT_FUNCTION_URL = None
            with pytest.raises(ValidationError, match="PDF_AUTOFILLER_FUNCTION_URL"):
                MapperClient(api_key=API_KEY)
        finally:
            _mod._DEFAULT_FUNCTION_URL = original

    def test_valid_init(self):
        client = _client()
        assert client is not None
        client.close()

    def test_context_manager(self):
        with _client() as client:
            assert client is not None


class TestMakeEmbedFile:
    def test_success(self):
        expected = {"cache_hit": False, "embedded_pdf": "s3://bucket/embedded.pdf"}
        with patch.object(httpx.Client, "post", return_value=_make_response(expected)):
            with _client() as client:
                result = client.make_embed_file(
                    user_id=1, pdf_doc_id=42, session_id="sess-1", env="prod"
                )
        assert result == expected

    def test_sends_correct_operation(self):
        with patch.object(httpx.Client, "post", return_value=_make_response({})) as mock_post:
            with _client() as client:
                client.make_embed_file(
                    user_id=1, pdf_doc_id=42, session_id="s", env="prod",
                    investor_type="institutional", use_second_mapper=True,
                    developer_id="dev-1",
                )
        payload = mock_post.call_args.kwargs["json"]
        assert payload["operation"] == "make_embed_file"
        assert payload["user_id"] == 1
        assert payload["pdf_doc_id"] == 42
        assert payload["investor_type"] == "institutional"
        assert payload["use_second_mapper"] is True
        assert payload["developer_id"] == "dev-1"

    def test_developer_id_omitted_when_none(self):
        with patch.object(httpx.Client, "post", return_value=_make_response({})) as mock_post:
            with _client() as client:
                client.make_embed_file(user_id=1, pdf_doc_id=1, session_id="s", env="prod")
        payload = mock_post.call_args.kwargs["json"]
        assert "developer_id" not in payload


class TestFillPdf:
    def test_success(self):
        expected = {"filled_pdf": "s3://bucket/filled.pdf"}
        with patch.object(httpx.Client, "post", return_value=_make_response(expected)):
            with _client() as client:
                result = client.fill_pdf(
                    user_id=1, pdf_doc_id=42, session_id="sess-1", env="prod"
                )
        assert result == expected

    def test_sends_correct_operation(self):
        with patch.object(httpx.Client, "post", return_value=_make_response({})) as mock_post:
            with _client() as client:
                client.fill_pdf(user_id=5, pdf_doc_id=10, session_id="s", env="dev")
        payload = mock_post.call_args.kwargs["json"]
        assert payload["operation"] == "fill_pdf"
        assert payload["user_id"] == 5
        assert payload["env"] == "dev"


class TestCheckEmbedFile:
    def test_success(self):
        expected = {"cache_hit": True, "embedded_pdf": "s3://bucket/embedded.pdf"}
        with patch.object(httpx.Client, "post", return_value=_make_response(expected)):
            with _client() as client:
                result = client.check_embed_file(
                    user_id=1, pdf_doc_id=42, session_id="sess-1", env="prod"
                )
        assert result["cache_hit"] is True

    def test_sends_correct_operation(self):
        with patch.object(httpx.Client, "post", return_value=_make_response({})) as mock_post:
            with _client() as client:
                client.check_embed_file(user_id=2, pdf_doc_id=7, session_id="s", env="prod")
        payload = mock_post.call_args.kwargs["json"]
        assert payload["operation"] == "check_embed_file"


class TestErrorHandling:
    def test_401_raises_authentication_error(self):
        mock_resp = _make_error_response(401, "Missing X-API-Key header")
        with patch.object(httpx.Client, "post", return_value=mock_resp):
            with MapperClient(function_url=FUNCTION_URL, api_key="bad") as client:
                with pytest.raises(AuthenticationError):
                    client.make_embed_file(user_id=1, pdf_doc_id=1, session_id="s", env="prod")

    def test_403_raises_authentication_error(self):
        mock_resp = _make_error_response(403, "Invalid API token")
        with patch.object(httpx.Client, "post", return_value=mock_resp):
            with MapperClient(function_url=FUNCTION_URL, api_key="bad") as client:
                with pytest.raises(AuthenticationError):
                    client.fill_pdf(user_id=1, pdf_doc_id=1, session_id="s", env="prod")

    def test_400_raises_validation_error(self):
        mock_resp = _make_error_response(400, "Missing required parameter: env")
        with patch.object(httpx.Client, "post", return_value=mock_resp):
            with _client() as client:
                with pytest.raises(ValidationError, match="env"):
                    client.check_embed_file(user_id=1, pdf_doc_id=1, session_id="s", env="prod")

    def test_500_raises_api_error(self):
        mock_resp = _make_error_response(500, "Processing failed", error="RuntimeError")
        with patch.object(httpx.Client, "post", return_value=mock_resp):
            with _client() as client:
                with pytest.raises(APIError) as exc_info:
                    client.make_embed_file(user_id=1, pdf_doc_id=1, session_id="s", env="prod")
        assert exc_info.value.status_code == 500

    def test_timeout_raises_timeout_error(self):
        with patch.object(
            httpx.Client, "post", side_effect=httpx.TimeoutException("timed out")
        ):
            with _client() as client:
                with pytest.raises(TimeoutError):
                    client.make_embed_file(user_id=1, pdf_doc_id=1, session_id="s", env="prod")

    def test_network_error_raises_api_error(self):
        with patch.object(
            httpx.Client, "post", side_effect=httpx.ConnectError("connection refused")
        ):
            with _client() as client:
                with pytest.raises(APIError):
                    client.fill_pdf(user_id=1, pdf_doc_id=1, session_id="s", env="prod")
