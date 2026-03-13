"""
Tests for handle_fill_operation and fill_with_java / fill_with_java_safe.
Java subprocess is mocked throughout.
"""

import pytest
import asyncio
import subprocess
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# fill_with_java — unit tests
# ---------------------------------------------------------------------------

class TestFillWithJava:
    def _run(self, coro):
        return asyncio.run(coro)

    @patch("src.fillers.fill_pdf.subprocess.run")
    @patch("src.fillers.fill_pdf.os.path.exists")
    def test_returns_output_path_on_success(self, mock_exists, mock_sub, tmp_path):
        import os
        embedded = str(tmp_path / "embedded.pdf")
        input_json = str(tmp_path / "data.json")
        jar = "filler.jar"

        # Mirror the source code's output path logic so the test works on
        # both macOS (tmp_path=/private/var/...) and Linux CI (tmp_path=/tmp/...)
        base = os.path.splitext(os.path.basename(embedded))[0]
        if "/tmp/" in embedded:
            expected_out = f"/tmp/{base}_filled.pdf"
        else:
            expected_out = f"{os.path.splitext(embedded)[0]}_filled.pdf"

        mock_exists.side_effect = lambda p: p in {jar, embedded, input_json, expected_out}
        mock_sub.return_value = MagicMock(returncode=0)

        from src.fillers.fill_pdf import fill_with_java
        result = self._run(fill_with_java(embedded, input_json))
        assert result.endswith("_filled.pdf")

    @patch("src.fillers.fill_pdf.subprocess.run")
    @patch("src.fillers.fill_pdf.os.path.exists")
    def test_raises_when_jar_not_found(self, mock_exists, mock_sub):
        mock_exists.return_value = False

        from src.fillers.fill_pdf import fill_with_java
        with pytest.raises(FileNotFoundError, match="filler"):
            self._run(fill_with_java("emb.pdf", "data.json"))

    @patch("src.fillers.fill_pdf.subprocess.run")
    @patch("src.fillers.fill_pdf.os.path.exists")
    def test_raises_on_java_failure(self, mock_exists, mock_sub, tmp_path):
        embedded = str(tmp_path / "emb.pdf"); open(embedded, "wb").close()
        input_json = str(tmp_path / "data.json"); open(input_json, "w").write("{}")
        jar = "filler.jar"

        mock_exists.side_effect = lambda p: p in {jar, embedded, input_json}
        mock_sub.side_effect = subprocess.CalledProcessError(1, "java", stderr="NullPointer")

        from src.fillers.fill_pdf import fill_with_java
        with pytest.raises(RuntimeError, match="NullPointer"):
            self._run(fill_with_java(embedded, input_json))

    @patch("src.fillers.fill_pdf.subprocess.run")
    @patch("src.fillers.fill_pdf.os.path.exists")
    def test_raises_on_timeout(self, mock_exists, mock_sub, tmp_path):
        embedded = str(tmp_path / "emb.pdf"); open(embedded, "wb").close()
        input_json = str(tmp_path / "data.json"); open(input_json, "w").write("{}")
        jar = "filler.jar"

        mock_exists.side_effect = lambda p: p in {jar, embedded, input_json}
        mock_sub.side_effect = subprocess.TimeoutExpired("java", 300)

        from src.fillers.fill_pdf import fill_with_java
        with pytest.raises(RuntimeError, match="timed out"):
            self._run(fill_with_java(embedded, input_json))


# ---------------------------------------------------------------------------
# fill_with_java_safe — never raises, returns status dict
# ---------------------------------------------------------------------------

class TestFillWithJavaSafe:
    def _run(self, coro):
        return asyncio.run(coro)

    @patch("src.fillers.fill_pdf.fill_with_java")
    @patch("src.fillers.fill_pdf.os.path.exists")
    def test_success_returns_status_dict(self, mock_exists, mock_fill, tmp_path):
        embedded = str(tmp_path / "emb.pdf")
        input_json = str(tmp_path / "data.json")
        mock_exists.return_value = True
        mock_fill.return_value = str(tmp_path / "filled.pdf")

        from src.fillers.fill_pdf import fill_with_java_safe
        result = self._run(fill_with_java_safe(embedded, input_json))

        assert result["status"] == "success"
        assert result["pdf_file_path"] is not None

    @patch("src.fillers.fill_pdf.os.path.exists")
    def test_missing_embedded_pdf_returns_error(self, mock_exists):
        mock_exists.return_value = False

        from src.fillers.fill_pdf import fill_with_java_safe
        result = self._run(fill_with_java_safe("nonexistent.pdf", "data.json"))

        assert result["status"] == "error"
        assert "error" in result

    @patch("src.fillers.fill_pdf.fill_with_java")
    @patch("src.fillers.fill_pdf.os.path.exists")
    def test_java_exception_returns_error(self, mock_exists, mock_fill, tmp_path):
        embedded = str(tmp_path / "emb.pdf")
        mock_exists.return_value = True
        mock_fill.side_effect = RuntimeError("Java crash")

        from src.fillers.fill_pdf import fill_with_java_safe
        result = self._run(fill_with_java_safe(embedded, "data.json"))

        assert result["status"] == "error"
        assert "Java crash" in result["error"]

    @patch("src.fillers.fill_pdf.fill_with_java")
    @patch("src.fillers.fill_pdf.os.path.exists")
    def test_never_raises(self, mock_exists, mock_fill, tmp_path):
        """fill_with_java_safe must always return a dict, never raise."""
        embedded = str(tmp_path / "emb.pdf")
        mock_exists.return_value = True
        mock_fill.side_effect = Exception("anything")

        from src.fillers.fill_pdf import fill_with_java_safe
        result = self._run(fill_with_java_safe(embedded, "data.json"))
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# handle_fill_operation — handler-level tests
# ---------------------------------------------------------------------------

@pytest.fixture
def fill_config(tmp_path):
    cfg = MagicMock()
    cfg.source_type = "local"
    cfg.local_filled_pdf = str(tmp_path / "filled.pdf")
    return cfg


def _fill_handlers(embedded, input_json):
    in_h = MagicMock()
    in_h.get_input.side_effect = lambda key: {
        "embedded_pdf": embedded,
        "input_json": input_json,
    }.get(key)
    out_h = MagicMock()
    out_h.save_output.return_value = "/saved/filled.pdf"
    return in_h, out_h


class TestHandleFillOperation:
    def _run(self, coro):
        return asyncio.run(coro)

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.fill_with_java")
    def test_success_response_shape(self, mock_java, mock_fh, fill_config, tmp_path):
        embedded = str(tmp_path / "emb.pdf"); open(embedded, "wb").close()
        input_json = str(tmp_path / "data.json"); open(input_json, "w").write("{}")

        mock_fh.return_value = _fill_handlers(embedded, input_json)
        mock_java.return_value = str(tmp_path / "filled.pdf")

        from src.handlers.operations import handle_fill_operation
        result = self._run(handle_fill_operation(fill_config))

        assert result["status"] == "success"
        assert result["operation"] == "fill"
        assert "output_file" in result

    @patch("src.handlers.operations.create_file_handlers")
    def test_missing_embedded_pdf_raises(self, mock_fh, fill_config):
        in_h = MagicMock(); in_h.get_input.return_value = None
        mock_fh.return_value = (in_h, MagicMock())

        from src.handlers.operations import handle_fill_operation
        with pytest.raises(FileNotFoundError):
            self._run(handle_fill_operation(fill_config))

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.fill_with_java")
    def test_java_error_propagates(self, mock_java, mock_fh, fill_config, tmp_path):
        embedded = str(tmp_path / "emb.pdf"); open(embedded, "wb").close()
        input_json = str(tmp_path / "data.json"); open(input_json, "w").write("{}")

        mock_fh.return_value = _fill_handlers(embedded, input_json)
        mock_java.side_effect = RuntimeError("filler failed")

        from src.handlers.operations import handle_fill_operation
        with pytest.raises(RuntimeError, match="filler failed"):
            self._run(handle_fill_operation(fill_config))
