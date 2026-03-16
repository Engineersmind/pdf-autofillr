"""
Tests for handle_extract_operation.
All external I/O (extractor, file system, notifications) is mocked.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_config(tmp_path):
    cfg = MagicMock()
    cfg.source_type = "local"
    cfg.local_extracted_json = str(tmp_path / "extracted.json")
    return cfg


def _make_handlers(pdf_path):
    in_h = MagicMock()
    in_h.get_input.side_effect = lambda key: pdf_path if key == "input_pdf" else None
    out_h = MagicMock()
    out_h.save_output.return_value = "/saved/extracted.json"
    return in_h, out_h


def _extractor_result(n_fields=3, pdf_hash="abc123"):
    return {"pdf_hash": pdf_hash, "fields": [{"fid": i} for i in range(n_fields)], "pages": []}


class TestHandleExtractOperation:
    def _run(self, coro):
        return asyncio.run(coro)

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.DetailedFitzExtractor")
    def test_success_response_shape(self, MockExt, mock_fh, mock_config, tmp_path):
        pdf = str(tmp_path / "form.pdf"); open(pdf, "wb").close()
        mock_fh.return_value = _make_handlers(pdf)
        MockExt.return_value.extract.return_value = _extractor_result()

        from src.handlers.operations import handle_extract_operation
        result = self._run(handle_extract_operation(mock_config))

        assert result["status"] == "success"
        assert result["operation"] == "extract"
        assert "output_file" in result
        assert "execution_time_seconds" in result

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.DetailedFitzExtractor")
    def test_pdf_hash_forwarded(self, MockExt, mock_fh, mock_config, tmp_path):
        pdf = str(tmp_path / "form.pdf"); open(pdf, "wb").close()
        mock_fh.return_value = _make_handlers(pdf)
        MockExt.return_value.extract.return_value = _extractor_result(pdf_hash="deadbeef")

        from src.handlers.operations import handle_extract_operation
        result = self._run(handle_extract_operation(mock_config))
        assert result["pdf_hash"] == "deadbeef"

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.DetailedFitzExtractor")
    def test_output_handler_called_correctly(self, MockExt, mock_fh, mock_config, tmp_path):
        pdf = str(tmp_path / "form.pdf"); open(pdf, "wb").close()
        in_h, out_h = _make_handlers(pdf)
        mock_fh.return_value = (in_h, out_h)
        MockExt.return_value.extract.return_value = _extractor_result()

        from src.handlers.operations import handle_extract_operation
        self._run(handle_extract_operation(mock_config))
        out_h.save_output.assert_called_once_with(mock_config.local_extracted_json, "extracted_json")

    @patch("src.handlers.operations.create_file_handlers")
    def test_missing_pdf_raises(self, mock_fh, mock_config):
        in_h = MagicMock(); in_h.get_input.return_value = None
        mock_fh.return_value = (in_h, MagicMock())

        from src.handlers.operations import handle_extract_operation
        with pytest.raises(FileNotFoundError):
            self._run(handle_extract_operation(mock_config))

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.DetailedFitzExtractor")
    def test_extractor_error_propagates(self, MockExt, mock_fh, mock_config, tmp_path):
        pdf = str(tmp_path / "form.pdf"); open(pdf, "wb").close()
        mock_fh.return_value = _make_handlers(pdf)
        MockExt.return_value.extract.side_effect = RuntimeError("corrupt PDF")

        from src.handlers.operations import handle_extract_operation
        with pytest.raises(RuntimeError, match="corrupt PDF"):
            self._run(handle_extract_operation(mock_config))

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.DetailedFitzExtractor")
    def test_storage_type_in_response(self, MockExt, mock_fh, mock_config, tmp_path):
        mock_config.source_type = "aws"
        pdf = str(tmp_path / "form.pdf"); open(pdf, "wb").close()
        mock_fh.return_value = _make_handlers(pdf)
        MockExt.return_value.extract.return_value = _extractor_result()

        from src.handlers.operations import handle_extract_operation
        result = self._run(handle_extract_operation(mock_config))
        assert result["storage_type"] == "aws"
