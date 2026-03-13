"""
Tests for handle_embed_operation and run_embed_java_stage.
Java subprocess and file system are mocked throughout.
"""

import pytest
import asyncio
import subprocess
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# run_embed_java_stage — unit tests (mocks subprocess + os.path.exists)
# ---------------------------------------------------------------------------

class TestRunEmbedJavaStage:
    def _run(self, coro):
        return asyncio.run(coro)

    def _exists(self, truthy_paths):
        return lambda p: p in truthy_paths

    @patch("src.embedders.embed_keys.subprocess.run")
    @patch("src.embedders.embed_keys.os.path.exists")
    def test_returns_output_path_on_success(self, mock_exists, mock_sub, tmp_path):
        pdf = str(tmp_path / "form.pdf")
        ext = str(tmp_path / "extracted.json")
        mapping = str(tmp_path / "mapping.json")
        radio = str(tmp_path / "radio.json")
        jar = "rebuilder.jar"
        expected_out = f"{tmp_path}/form_embedded.pdf"

        # exists returns True for jar + all inputs + the output file
        mock_exists.side_effect = lambda p: p in {jar, pdf, ext, mapping, radio, expected_out}
        mock_sub.return_value = MagicMock(returncode=0, stdout="", stderr="")

        from src.embedders.embed_keys import run_embed_java_stage
        result = self._run(run_embed_java_stage(pdf, ext, mapping, radio))
        assert result.endswith("_embedded.pdf")

    @patch("src.embedders.embed_keys.subprocess.run")
    @patch("src.embedders.embed_keys.os.path.exists")
    def test_raises_when_jar_not_found(self, mock_exists, mock_sub):
        mock_exists.return_value = False   # nothing exists

        from src.embedders.embed_keys import run_embed_java_stage
        with pytest.raises(FileNotFoundError, match="rebuilder"):
            self._run(run_embed_java_stage("a.pdf", "b.json", "c.json", "d.json"))

    @patch("src.embedders.embed_keys.subprocess.run")
    @patch("src.embedders.embed_keys.os.path.exists")
    def test_raises_when_input_file_missing(self, mock_exists, mock_sub):
        # jar exists but input PDF does not
        mock_exists.side_effect = lambda p: p == "rebuilder.jar"

        from src.embedders.embed_keys import run_embed_java_stage
        with pytest.raises(FileNotFoundError, match="original_pdf"):
            self._run(run_embed_java_stage("missing.pdf", "b.json", "c.json", "d.json"))

    @patch("src.embedders.embed_keys.subprocess.run")
    @patch("src.embedders.embed_keys.os.path.exists")
    def test_raises_on_java_process_failure(self, mock_exists, mock_sub, tmp_path):
        pdf = str(tmp_path / "form.pdf"); open(pdf, "wb").close()
        ext = str(tmp_path / "ext.json"); open(ext, "w").write("{}")
        mapping = str(tmp_path / "map.json"); open(mapping, "w").write("{}")
        radio = str(tmp_path / "radio.json"); open(radio, "w").write("{}")
        jar = "rebuilder.jar"

        mock_exists.side_effect = lambda p: p in {jar, pdf, ext, mapping, radio}
        mock_sub.side_effect = subprocess.CalledProcessError(1, "java", stderr="OutOfMemoryError")

        from src.embedders.embed_keys import run_embed_java_stage
        with pytest.raises(RuntimeError, match="OutOfMemoryError"):
            self._run(run_embed_java_stage(pdf, ext, mapping, radio))

    @patch("src.embedders.embed_keys.subprocess.run")
    @patch("src.embedders.embed_keys.os.path.exists")
    def test_raises_on_java_timeout(self, mock_exists, mock_sub, tmp_path):
        pdf = str(tmp_path / "form.pdf"); open(pdf, "wb").close()
        ext = str(tmp_path / "ext.json"); open(ext, "w").write("{}")
        mapping = str(tmp_path / "map.json"); open(mapping, "w").write("{}")
        radio = str(tmp_path / "radio.json"); open(radio, "w").write("{}")
        jar = "rebuilder.jar"

        mock_exists.side_effect = lambda p: p in {jar, pdf, ext, mapping, radio}
        mock_sub.side_effect = subprocess.TimeoutExpired("java", 300)

        from src.embedders.embed_keys import run_embed_java_stage
        with pytest.raises(RuntimeError, match="timed out"):
            self._run(run_embed_java_stage(pdf, ext, mapping, radio))


# ---------------------------------------------------------------------------
# handle_embed_operation — handler-level tests
# ---------------------------------------------------------------------------

@pytest.fixture
def embed_config(tmp_path):
    cfg = MagicMock()
    cfg.source_type = "local"
    cfg.local_mapped_json = str(tmp_path / "mapping.json")
    cfg.local_radio_json = str(tmp_path / "radio.json")
    cfg.local_embedded_pdf = str(tmp_path / "embedded.pdf")
    cfg.dest_embedded_pdf = str(tmp_path / "dest_embedded.pdf")
    return cfg


def _embed_handlers(pdf, extracted):
    in_h = MagicMock()
    in_h.get_input.side_effect = lambda key: {"input_pdf": pdf, "extracted_json": extracted}.get(key)
    out_h = MagicMock()
    out_h.save_output.return_value = "/saved/embedded.pdf"
    return in_h, out_h


class TestHandleEmbedOperation:
    def _run(self, coro):
        return asyncio.run(coro)

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.run_embed_java_stage")
    def test_success_response_shape(self, mock_java, mock_fh, embed_config, tmp_path):
        pdf = str(tmp_path / "form.pdf"); open(pdf, "wb").close()
        ext = str(tmp_path / "ext.json"); open(ext, "w").write("{}")

        in_h, out_h = _embed_handlers(pdf, ext)
        mock_fh.return_value = (in_h, out_h)
        mock_java.return_value = str(tmp_path / "embedded.pdf")

        from src.handlers.operations import handle_embed_operation
        result = self._run(handle_embed_operation(embed_config))

        assert result["status"] == "success"
        assert result["operation"] == "embed"
        assert "execution_time_seconds" in result

    @patch("src.handlers.operations.create_file_handlers")
    def test_missing_input_raises(self, mock_fh, embed_config):
        in_h = MagicMock(); in_h.get_input.return_value = None
        mock_fh.return_value = (in_h, MagicMock())

        from src.handlers.operations import handle_embed_operation
        with pytest.raises(FileNotFoundError):
            self._run(handle_embed_operation(embed_config))

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.run_embed_java_stage")
    def test_java_failure_propagates(self, mock_java, mock_fh, embed_config, tmp_path):
        pdf = str(tmp_path / "form.pdf"); open(pdf, "wb").close()
        ext = str(tmp_path / "ext.json"); open(ext, "w").write("{}")

        mock_fh.return_value = _embed_handlers(pdf, ext)
        mock_java.side_effect = RuntimeError("Java OOM")

        from src.handlers.operations import handle_embed_operation
        with pytest.raises(RuntimeError, match="Java OOM"):
            self._run(handle_embed_operation(embed_config))
