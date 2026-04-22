"""Tests for embedders/embed_keys.py — run_embed_java_stage."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestRunEmbedJavaStage:
    async def test_raises_when_original_pdf_missing(self, tmp_path):
        from pdf_autofillr_mapper.embedders.embed_keys import run_embed_java_stage

        extracted = tmp_path / "extracted.json"
        extracted.write_text("{}")
        mapping = tmp_path / "mapping.json"
        mapping.write_text("{}")
        radio = tmp_path / "radio.json"
        radio.write_text("{}")

        with pytest.raises(FileNotFoundError):
            await run_embed_java_stage(
                str(tmp_path / "ghost.pdf"),
                str(extracted),
                str(mapping),
                str(radio),
            )

    async def test_raises_when_extracted_json_missing(self, tmp_path):
        from pdf_autofillr_mapper.embedders.embed_keys import run_embed_java_stage

        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        mapping = tmp_path / "mapping.json"
        mapping.write_text("{}")
        radio = tmp_path / "radio.json"
        radio.write_text("{}")

        with pytest.raises(FileNotFoundError):
            await run_embed_java_stage(
                str(pdf),
                str(tmp_path / "ghost.json"),
                str(mapping),
                str(radio),
            )

    async def test_uses_storage_config_path(self, tmp_path):
        from pdf_autofillr_mapper.embedders.embed_keys import run_embed_java_stage

        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        extracted = tmp_path / "extracted.json"
        extracted.write_text("{}")
        mapping = tmp_path / "mapping.json"
        mapping.write_text("{}")
        radio = tmp_path / "radio.json"
        radio.write_text("{}")
        output = tmp_path / "out" / "embedded.pdf"

        def fake_run(cmd, **_):
            Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(cmd[-1]).write_bytes(b"%PDF-1.4 embedded")
            result = MagicMock()
            result.stdout = ""
            result.returncode = 0
            return result

        with patch("subprocess.run", side_effect=fake_run):
            result = await run_embed_java_stage(
                str(pdf),
                str(extracted),
                str(mapping),
                str(radio),
                storage_config={"path": str(output)},
            )

        assert result == str(output)

    async def test_raises_on_java_process_error(self, tmp_path):
        import subprocess
        from pdf_autofillr_mapper.embedders.embed_keys import run_embed_java_stage

        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        extracted = tmp_path / "extracted.json"
        extracted.write_text("{}")
        mapping = tmp_path / "mapping.json"
        mapping.write_text("{}")
        radio = tmp_path / "radio.json"
        radio.write_text("{}")

        err = subprocess.CalledProcessError(1, "java", stderr="Java heap error")
        with patch("subprocess.run", side_effect=err):
            with pytest.raises((RuntimeError, FileNotFoundError)):
                await run_embed_java_stage(str(pdf), str(extracted), str(mapping), str(radio))

    async def test_raises_on_java_timeout(self, tmp_path):
        import subprocess
        from pdf_autofillr_mapper.embedders.embed_keys import run_embed_java_stage

        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        extracted = tmp_path / "extracted.json"
        extracted.write_text("{}")
        mapping = tmp_path / "mapping.json"
        mapping.write_text("{}")
        radio = tmp_path / "radio.json"
        radio.write_text("{}")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="java", timeout=300)):
            with pytest.raises((RuntimeError, FileNotFoundError)):
                await run_embed_java_stage(str(pdf), str(extracted), str(mapping), str(radio))
