"""Tests for fill_pdf.py — fill_with_java and fill_with_java_safe."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestFillWithJava:
    async def test_raises_when_embedded_pdf_missing(self, tmp_path):
        from pdf_autofillr_mapper.fillers.fill_pdf import fill_with_java

        input_json = tmp_path / "data.json"
        input_json.write_text("{}")
        with patch("pdf_autofillr_mapper.fillers.fill_pdf.find_jar", return_value="/fake/filler.jar"):
            with pytest.raises(FileNotFoundError, match="embedded_pdf"):
                await fill_with_java(str(tmp_path / "ghost.pdf"), str(input_json))

    async def test_raises_when_input_json_missing(self, tmp_path):
        from pdf_autofillr_mapper.fillers.fill_pdf import fill_with_java

        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        with patch("pdf_autofillr_mapper.fillers.fill_pdf.find_jar", return_value="/fake/filler.jar"):
            with pytest.raises(FileNotFoundError, match="input_json"):
                await fill_with_java(str(pdf), str(tmp_path / "ghost.json"))

    async def test_uses_explicit_output_path(self, tmp_path):
        from pdf_autofillr_mapper.fillers.fill_pdf import fill_with_java

        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        input_json = tmp_path / "data.json"
        input_json.write_text("{}")
        output_pdf = tmp_path / "out" / "filled.pdf"

        def fake_run(cmd, **_):
            Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(cmd[-1]).write_bytes(b"%PDF-1.4 filled")
            result = MagicMock()
            result.stdout = "Success"
            return result

        with patch("pdf_autofillr_mapper.fillers.fill_pdf.find_jar", return_value="/fake/filler.jar"):
            with patch("subprocess.run", side_effect=fake_run):
                result = await fill_with_java(str(pdf), str(input_json), output_path=str(output_pdf))

        assert result == str(output_pdf)

    async def test_raises_on_java_timeout(self, tmp_path):
        import subprocess
        from pdf_autofillr_mapper.fillers.fill_pdf import fill_with_java

        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        input_json = tmp_path / "data.json"
        input_json.write_text("{}")
        with patch("pdf_autofillr_mapper.fillers.fill_pdf.find_jar", return_value="/fake/filler.jar"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="java", timeout=300)):
                with pytest.raises(RuntimeError, match="timed out"):
                    await fill_with_java(str(pdf), str(input_json))

    async def test_raises_on_java_process_error(self, tmp_path):
        import subprocess
        from pdf_autofillr_mapper.fillers.fill_pdf import fill_with_java

        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        input_json = tmp_path / "data.json"
        input_json.write_text("{}")
        err = subprocess.CalledProcessError(1, "java", stderr="OutOfMemoryError")
        with patch("pdf_autofillr_mapper.fillers.fill_pdf.find_jar", return_value="/fake/filler.jar"):
            with patch("subprocess.run", side_effect=err):
                with pytest.raises(RuntimeError, match="OutOfMemoryError"):
                    await fill_with_java(str(pdf), str(input_json))

    async def test_raises_when_output_not_created(self, tmp_path):
        from pdf_autofillr_mapper.fillers.fill_pdf import fill_with_java

        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        input_json = tmp_path / "data.json"
        input_json.write_text("{}")

        def fake_run(cmd, **_):
            result = MagicMock()
            result.stdout = ""
            return result

        with patch("pdf_autofillr_mapper.fillers.fill_pdf.find_jar", return_value="/fake/filler.jar"):
            with patch("subprocess.run", side_effect=fake_run):
                with pytest.raises(RuntimeError, match="output file not found"):
                    await fill_with_java(str(pdf), str(input_json))


class TestFillWithJavaSafe:
    async def test_returns_error_when_embedded_pdf_missing(self, tmp_path):
        from pdf_autofillr_mapper.fillers.fill_pdf import fill_with_java_safe

        result = await fill_with_java_safe(str(tmp_path / "ghost.pdf"), str(tmp_path / "data.json"))
        assert result["status"] == "error"
        assert result["pdf_file_path"] is None
        assert "not found" in result["error"]

    async def test_returns_success_on_fill(self, tmp_path):
        from pdf_autofillr_mapper.fillers.fill_pdf import fill_with_java_safe

        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        input_json = tmp_path / "data.json"
        input_json.write_text("{}")
        filled = str(tmp_path / "filled.pdf")

        async def mock_fill(embedded, inp, storage_config=None):
            return filled

        with patch("pdf_autofillr_mapper.fillers.fill_pdf.fill_with_java", side_effect=mock_fill):
            result = await fill_with_java_safe(str(pdf), str(input_json))

        assert result["status"] == "success"
        assert result["pdf_file_path"] == filled

    async def test_returns_error_on_exception(self, tmp_path):
        from pdf_autofillr_mapper.fillers.fill_pdf import fill_with_java_safe

        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        async def mock_fill(*args, **_):
            raise RuntimeError("Java crash")

        with patch("pdf_autofillr_mapper.fillers.fill_pdf.fill_with_java", side_effect=mock_fill):
            result = await fill_with_java_safe(str(pdf), str(tmp_path / "data.json"))

        assert result["status"] == "error"
        assert "Java crash" in result["error"]
        assert result["pdf_file_path"] is None
