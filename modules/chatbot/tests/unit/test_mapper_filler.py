"""
Unit tests for MapperPDFFiller.

Covers Issues 1, 3, 4, 5:
  1 — URL prefix is appended correctly (/mapper by default)
  3 — investor_type is encoded in session_id label
  4 — doc_id extracted from outputs.embedded_pdf key
  5 — check_document_ready reads "exists" key correctly
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


@pytest.fixture
def filler():
    """MapperPDFFiller with a mocked PDFMapperClient."""
    from src.chatbot.pdf.mapper_filler import MapperPDFFiller
    f = MapperPDFFiller(
        mapper_api_url="http://localhost:8000",
        mapper_api_key="test-key",
    )
    # Inject a mock client
    mock_client = MagicMock()
    f._client = mock_client
    return f, mock_client


# ── Issue 1: URL prefix ───────────────────────────────────────────────

def test_default_url_prefix_is_mapper():
    from src.chatbot.pdf.mapper_filler import MapperPDFFiller
    f = MapperPDFFiller(mapper_api_url="http://myserver:9000")
    assert f._api_url == "http://myserver:9000/mapper"


def test_custom_url_prefix_empty():
    from src.chatbot.pdf.mapper_filler import MapperPDFFiller
    f = MapperPDFFiller(mapper_api_url="http://myserver:9000", url_prefix="")
    assert f._api_url == "http://myserver:9000"


def test_url_prefix_from_env(monkeypatch):
    monkeypatch.setenv("MAPPER_URL_PREFIX", "/api/v1")
    from importlib import reload
    import src.chatbot.pdf.mapper_filler as mod
    reload(mod)
    f = mod.MapperPDFFiller(mapper_api_url="http://myserver:9000")
    assert f._api_url == "http://myserver:9000/api/v1"


# ── Issue 3: investor_type in session label ───────────────────────────

def test_prepare_document_encodes_investor_type(filler):
    f, mock_client = filler
    mock_client.mapper.make_embed_file.return_value = {
        "data": {"outputs": {"embedded_pdf": "/tmp/embedded.pdf"}}
    }

    doc_id = f.prepare_document("/tmp/form.pdf", "Corporation")

    call_kwargs = mock_client.mapper.make_embed_file.call_args
    session_id_arg = call_kwargs.kwargs.get("session_id") or call_kwargs.args[1]
    assert "corporation" in session_id_arg.lower()


# ── Issue 4: doc_id extraction ────────────────────────────────────────

def test_prepare_document_extracts_outputs_embedded_pdf(filler):
    """Primary path: outputs.embedded_pdf key."""
    f, mock_client = filler
    mock_client.mapper.make_embed_file.return_value = {
        "data": {"outputs": {"embedded_pdf": "/output/embedded.pdf"}}
    }
    doc_id = f.prepare_document("/tmp/form.pdf", "Individual")
    assert doc_id == "/output/embedded.pdf"


def test_prepare_document_fallback_to_embedded_pdf_flat(filler):
    """Flat key fallback: data.embedded_pdf."""
    f, mock_client = filler
    mock_client.mapper.make_embed_file.return_value = {
        "data": {"embedded_pdf": "/output/flat.pdf"}
    }
    doc_id = f.prepare_document("/tmp/form.pdf", "Individual")
    assert doc_id == "/output/flat.pdf"


def test_prepare_document_fallback_to_embedded_pdf_path_key(filler):
    """Legacy key fallback: data.embedded_pdf_path."""
    f, mock_client = filler
    mock_client.mapper.make_embed_file.return_value = {
        "data": {"embedded_pdf_path": "/output/legacy.pdf"}
    }
    doc_id = f.prepare_document("/tmp/form.pdf", "Individual")
    assert doc_id == "/output/legacy.pdf"


def test_prepare_document_fallback_to_input_pdf_when_no_key(filler, capsys):
    """When no known key found, fall back to input pdf_path and warn."""
    f, mock_client = filler
    mock_client.mapper.make_embed_file.return_value = {
        "data": {"some_unexpected_key": "value"}
    }
    doc_id = f.prepare_document("/tmp/form.pdf", "Individual")
    assert doc_id == "/tmp/form.pdf"


# ── Issue 5: check_document_ready ─────────────────────────────────────

def test_check_document_ready_exists_true(filler):
    """Primary: 'exists' key = True."""
    f, mock_client = filler
    mock_client.mapper.check_embed_file.return_value = {
        "data": {"exists": True, "status": "success"}
    }
    assert f.check_document_ready("/output/embedded.pdf") is True


def test_check_document_ready_exists_false(filler):
    """Primary: 'exists' key = False."""
    f, mock_client = filler
    mock_client.mapper.check_embed_file.return_value = {
        "data": {"exists": False, "status": "not_found"}
    }
    assert f.check_document_ready("/output/embedded.pdf") is False


def test_check_document_ready_status_success(filler):
    """Secondary fallback: status='success' when no exists key."""
    f, mock_client = filler
    mock_client.mapper.check_embed_file.return_value = {
        "data": {"status": "success"}
    }
    assert f.check_document_ready("/output/embedded.pdf") is True


def test_check_document_ready_status_not_found(filler):
    f, mock_client = filler
    mock_client.mapper.check_embed_file.return_value = {
        "data": {"status": "not_found"}
    }
    assert f.check_document_ready("/output/embedded.pdf") is False


def test_check_document_ready_legacy_has_metadata(filler):
    """Tertiary legacy key fallback."""
    f, mock_client = filler
    mock_client.mapper.check_embed_file.return_value = {
        "data": {"has_metadata": True}
    }
    assert f.check_document_ready("/output/embedded.pdf") is True


# ── fill_document ──────────────────────────────────────────────────────

def test_fill_document_calls_mapper_fill(filler):
    f, mock_client = filler
    mock_client.mapper.fill.return_value = {"status": "success", "filled_pdf": "/out/filled.pdf"}
    data = {"full_name": "Alice", "email": "alice@test.com"}
    result = f.fill_document("/output/embedded.pdf", data)
    mock_client.mapper.fill.assert_called_once_with(
        pdf_path="/output/embedded.pdf", data=data
    )
    assert result["status"] == "success"


# ── ImportError ───────────────────────────────────────────────────────

def test_get_client_raises_on_missing_sdk(monkeypatch):
    from src.chatbot.pdf.mapper_filler import MapperPDFFiller
    f = MapperPDFFiller()
    f._client = None

    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "pdf_autofiller":
            raise ImportError("no module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    with pytest.raises(ImportError, match="pdf-autofiller-sdk"):
        f._get_client()
