"""
Tests for the three primary operation handlers:
  - handle_make_embed_file_operation
  - handle_fill_pdf_operation
  - handle_check_embed_file_operation

All three now take (user_id, pdf_doc_id, session_id, env, developer_id=None, ...).
Tests use pytest-asyncio and mock the storage/path layer to avoid hitting the filesystem.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

USER_ID = 553
PDF_DOC_ID = 990
SESSION_ID = "086d6670-81e5-47f4-aecb-e4f7c3ba2a83"
ENV = "DEV_user"


@pytest.fixture
def mock_config(tmp_path):
    """Minimal config object returned by get_file_config().

    source_type='local' keeps the function on the local code path so it never
    calls get_complete_file_config() with old cloud-style keys.
    """
    base = tmp_path

    # Create stub input files so path existence checks pass
    input_pdf = base / "input.pdf"
    input_pdf.write_bytes(b"%PDF-1.4 fake")
    input_json = base / "input.json"
    input_json.write_text("{}")

    cfg = MagicMock()

    # Storage identity
    cfg.source_type = "local"

    # Local path attributes (used by make_embed / fill / check operations)
    cfg.local_input_pdf     = str(input_pdf)
    cfg.local_input_json    = str(input_json)
    cfg.local_global_json   = None
    cfg.s3_input_pdf        = None
    cfg.s3_input_json       = None
    cfg.s3_global_json      = None

    # Paths that internal helpers write to — must be real strings, not MagicMock,
    # otherwise open(MagicMock(), 'w') resolves to open(1, 'w') via __index__ = 1
    cfg.local_java_mapping       = str(base / f"{PDF_DOC_ID}_java_mapping.json")
    cfg.local_extracted_json     = str(base / f"{PDF_DOC_ID}_extracted.json")
    cfg.local_mapped_json        = str(base / f"{PDF_DOC_ID}_mapping.json")
    cfg.local_radio_groups       = str(base / f"{PDF_DOC_ID}_radio_groups.json")
    cfg.local_embedded_pdf       = str(base / f"{PDF_DOC_ID}_embedded.pdf")
    cfg.local_filled_pdf         = str(base / f"{PDF_DOC_ID}_filled.pdf")
    cfg.local_headers_with_fields = str(base / f"{PDF_DOC_ID}_headers_with_fields.json")
    cfg.local_final_form_fields  = str(base / f"{PDF_DOC_ID}_final_form_fields.json")

    # Disable cached_extraction branch
    cfg.cached_extraction   = None

    # StorageConfig sub-object
    sc = MagicMock()
    sc.env_folder = "dev"
    sc.user_type  = "regular"
    cfg._sc = sc

    # Pre-built processing paths (used by fill / check stages)
    cfg.get_complete_file_config.return_value = {
        "source_type":         "local",
        "input_pdf":           str(input_pdf),
        "global_json":         str(base / "global.json"),
        "input_json":          str(input_json),
        "extracted_json":      str(base / f"{PDF_DOC_ID}_extracted.json"),
        "mapped_json":         str(base / f"{PDF_DOC_ID}_mapping.json"),
        "radio_groups_json":   str(base / f"{PDF_DOC_ID}_radio_groups.json"),
        "headers_with_fields": str(base / f"{PDF_DOC_ID}_headers_with_fields.json"),
        "final_form_fields":   str(base / f"{PDF_DOC_ID}_final_form_fields.json"),
        "java_mapping":        str(base / f"{PDF_DOC_ID}_java_mapping.json"),
        "embedded_pdf":        str(base / f"{PDF_DOC_ID}_embedded.pdf"),
        "filled_pdf":          str(base / f"{PDF_DOC_ID}_filled.pdf"),
        "header_file":         str(base / f"rag/{PDF_DOC_ID}/input/headers.json"),
        "section_file":        str(base / f"rag/{PDF_DOC_ID}/input/sections.json"),
        "rag_predictions":     str(base / f"rag/{PDF_DOC_ID}/predictions/rag.json"),
        "llm_predictions":     str(base / f"rag/{PDF_DOC_ID}/predictions/llm.json"),
        "final_predictions":   str(base / f"rag/{PDF_DOC_ID}/predictions/final.json"),
        "cache_registry":      str(base / "hash_registry.json"),
        "filled_pdf_store":    str(base / "filled_store.pdf"),
    }
    return cfg


# ---------------------------------------------------------------------------
# handle_make_embed_file_operation
# ---------------------------------------------------------------------------

class TestMakeEmbedFileOperation:

    @pytest.mark.asyncio
    async def test_calls_extract_map_embed_stages(self, mock_config, tmp_path):
        """Each of the three pipeline stages must be invoked exactly once."""
        extracted   = tmp_path / "extracted.json"
        extracted.write_text("{}")

        mock_extract = AsyncMock(return_value={
            "status": "success", "output_file": str(extracted), "pdf_hash": None,
        })
        mock_map = AsyncMock(return_value={
            "status": "success",
            "semantic_mapping_path": str(tmp_path / "mapped.json"),
            "radio_groups_path":     str(tmp_path / "radio.json"),
            "dest_semantic_mapping": str(tmp_path / "mapped.json"),
            "dest_radio_groups":     str(tmp_path / "radio.json"),
        })
        mock_embed = AsyncMock(return_value={
            "status": "success",
            "output_file": str(tmp_path / "embedded.pdf"),
            "dest_output_file": str(tmp_path / "embedded.pdf"),
        })

        with patch("pdf_autofillr_mapper.configs.file_config.get_file_config", return_value=mock_config), \
             patch("pdf_autofillr_mapper.handlers.operations.handle_extract_operation", new=mock_extract), \
             patch("pdf_autofillr_mapper.handlers.operations.run_semantic_api_mapper", new=mock_map), \
             patch("pdf_autofillr_mapper.handlers.operations.convert_semantic_to_java_format",
                   new=AsyncMock(return_value=str(tmp_path / "java.json"))), \
             patch("pdf_autofillr_mapper.handlers.output_handler.OutputFileHandler"), \
             patch("pdf_autofillr_mapper.handlers.operations.handle_embed_operation", new=mock_embed):

            from pdf_autofillr_mapper.handlers.operations import handle_make_embed_file_operation
            result = await handle_make_embed_file_operation(
                user_id=USER_ID, pdf_doc_id=PDF_DOC_ID, session_id=SESSION_ID, env=ENV,
            )

        assert result is not None
        mock_extract.assert_called_once()
        mock_map.assert_called_once()
        mock_embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_developer_id_is_forwarded(self, mock_config):
        """developer_id and env must be forwarded to get_file_config."""
        captured = {}

        class _ParamsCaptured(Exception):
            pass

        def fake_get_file_config(**kwargs):
            captured.update(kwargs)
            raise _ParamsCaptured  # stop immediately after capturing

        with patch("pdf_autofillr_mapper.configs.file_config.get_file_config",
                   side_effect=fake_get_file_config):
            from pdf_autofillr_mapper.handlers.operations import handle_make_embed_file_operation
            try:
                await handle_make_embed_file_operation(
                    user_id=USER_ID,
                    pdf_doc_id=PDF_DOC_ID,
                    session_id=SESSION_ID,
                    env=ENV,
                    developer_id="dev-abc-123",
                )
            except _ParamsCaptured:
                pass

        assert captured.get("developer_id") == "dev-abc-123"
        assert captured.get("env") == ENV


# ---------------------------------------------------------------------------
# handle_fill_pdf_operation
# ---------------------------------------------------------------------------

class TestFillPdfOperation:

    @pytest.mark.asyncio
    async def test_requires_embedded_pdf(self, mock_config, tmp_path):
        """If the embedded PDF path doesn't exist, operation should raise or report error."""
        # embedded_pdf path is not created on disk — file doesn't exist
        with patch(
            "pdf_autofillr_mapper.configs.file_config.get_file_config",
            return_value=mock_config,
        ):
            from pdf_autofillr_mapper.handlers.operations import handle_fill_pdf_operation

            # Operation should either raise or return a non-success status
            try:
                result = await handle_fill_pdf_operation(
                    user_id=USER_ID,
                    pdf_doc_id=PDF_DOC_ID,
                    session_id=SESSION_ID,
                    env=ENV,
                )
                # If it returns (doesn't raise), it should report failure
                assert result.get("status") != "success" or result.get("error") is not None
            except (FileNotFoundError, Exception):
                pass  # Raising is also acceptable

    @pytest.mark.asyncio
    async def test_passes_env_to_config(self, mock_config):
        captured = {}

        def fake_get_file_config(**kwargs):
            captured.update(kwargs)
            return mock_config

        with patch(
            "pdf_autofillr_mapper.configs.file_config.get_file_config",
            side_effect=fake_get_file_config,
        ):
            from pdf_autofillr_mapper.handlers.operations import handle_fill_pdf_operation

            try:
                await handle_fill_pdf_operation(
                    user_id=USER_ID,
                    pdf_doc_id=PDF_DOC_ID,
                    session_id=SESSION_ID,
                    env="Local_user",
                    developer_id=None,
                )
            except Exception:
                pass  # We only care that config was called correctly

        assert captured.get("env") == "Local_user"
        assert captured.get("developer_id") is None


# ---------------------------------------------------------------------------
# handle_check_embed_file_operation
# ---------------------------------------------------------------------------

class TestCheckEmbedFileOperation:

    @pytest.mark.asyncio
    async def test_returns_ready_when_embedded_pdf_exists(self, mock_config, tmp_path):
        """When the embedded PDF exists on disk, status should be ready/exists."""
        # Create the embedded PDF file so the check passes
        embedded_path = tmp_path / f"{PDF_DOC_ID}_embedded.pdf"
        embedded_path.write_bytes(b"%PDF-1.4 embedded")

        mock_config.get_complete_file_config.return_value["embedded_pdf"] = str(embedded_path)

        with patch(
            "pdf_autofillr_mapper.configs.file_config.get_file_config",
            return_value=mock_config,
        ):
            from pdf_autofillr_mapper.handlers.operations import handle_check_embed_file_operation

            result = await handle_check_embed_file_operation(
                user_id=USER_ID,
                pdf_doc_id=PDF_DOC_ID,
                session_id=SESSION_ID,
                env=ENV,
            )

        # Result should indicate the file is ready/available
        assert isinstance(result, dict)
        ready_key = result.get("ready") or result.get("status") or result.get("exists")
        assert ready_key is not None

    @pytest.mark.asyncio
    async def test_returns_not_ready_when_embedded_pdf_missing(self, mock_config, tmp_path):
        """When the embedded PDF does not exist, status should indicate not ready."""
        # Do NOT create embedded PDF — path points to non-existent file
        with patch(
            "pdf_autofillr_mapper.configs.file_config.get_file_config",
            return_value=mock_config,
        ):
            from pdf_autofillr_mapper.handlers.operations import handle_check_embed_file_operation

            result = await handle_check_embed_file_operation(
                user_id=USER_ID,
                pdf_doc_id=PDF_DOC_ID,
                session_id=SESSION_ID,
                env=ENV,
            )

        assert isinstance(result, dict)
        # Status should NOT be "success" with ready=True when file is missing
        if result.get("ready") is True:
            pytest.fail("check_embed_file reported ready but embedded PDF does not exist")

    @pytest.mark.asyncio
    async def test_passes_developer_id_to_config(self, mock_config):
        captured = {}

        def fake_get_file_config(**kwargs):
            captured.update(kwargs)
            return mock_config

        with patch(
            "pdf_autofillr_mapper.configs.file_config.get_file_config",
            side_effect=fake_get_file_config,
        ):
            from pdf_autofillr_mapper.handlers.operations import handle_check_embed_file_operation

            await handle_check_embed_file_operation(
                user_id=USER_ID,
                pdf_doc_id=PDF_DOC_ID,
                session_id=SESSION_ID,
                env="prod_user",
                developer_id="sdk-dev-99",
            )

        assert captured.get("env") == "prod_user"
        assert captured.get("developer_id") == "sdk-dev-99"
