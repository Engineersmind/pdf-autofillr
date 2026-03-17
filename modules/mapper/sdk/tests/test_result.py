"""
Tests for pdf_autofiller_mapper.result — SDKResult and StageResult.

No I/O, no mocking — exercises the dataclass logic and factory methods.
"""

import os
import shutil
import pytest
from pdf_autofiller_mapper.result import SDKResult, StageResult


# ---------------------------------------------------------------------------
# StageResult
# ---------------------------------------------------------------------------

class TestStageResult:
    def test_ok_when_success(self):
        sr = StageResult(stage="extract", status="success")
        assert sr.ok is True

    def test_not_ok_when_error(self):
        sr = StageResult(stage="map", status="error", error="LLM failed")
        assert sr.ok is False

    def test_defaults(self):
        sr = StageResult(stage="fill", status="success")
        assert sr.output_file is None
        assert sr.execution_time == 0.0
        assert sr.error is None
        assert sr.meta == {}


# ---------------------------------------------------------------------------
# SDKResult.failure
# ---------------------------------------------------------------------------

class TestSDKResultFailure:
    def test_status_is_error(self):
        r = SDKResult.failure("something went wrong")
        assert r.ok is False
        assert r.status == "error"
        assert r.error == "something went wrong"

    def test_execution_time(self):
        r = SDKResult.failure("oops", execution_time=1.5)
        assert r.execution_time == 1.5

    def test_defaults_are_empty(self):
        r = SDKResult.failure("err")
        assert r.filled_pdf is None
        assert r.mapping == {}
        assert r.stages == {}
        assert r.total_fields == 0


# ---------------------------------------------------------------------------
# SDKResult.from_operation
# ---------------------------------------------------------------------------

class TestSDKResultFromOperation:
    def _make_raw(self, **overrides):
        base = {
            "status": "success",
            "execution_time": 10.0,
            "pipeline_results": {
                "extract": {"status": "success", "output_file": "/tmp/ext.json",
                            "execution_time": 2.0},
                "map": {"status": "success", "output_file": "/tmp/map.json",
                        "execution_time": 4.0,
                        "mapping": {"1": "firstName", "2": "lastName"},
                        "confidence": 0.91, "total_fields_mapped": 2},
                "embed": {"status": "success", "output_file": "/tmp/emb.pdf",
                          "execution_time": 1.5},
                "fill": {"status": "success", "output_file": "/tmp/filled.pdf",
                         "execution_time": 2.5},
            },
        }
        base.update(overrides)
        return base

    def test_ok_on_success(self):
        r = SDKResult.from_operation(self._make_raw(), filled_pdf="/tmp/filled.pdf")
        assert r.ok is True

    def test_mapping_extracted(self):
        r = SDKResult.from_operation(self._make_raw())
        assert r.mapping == {"1": "firstName", "2": "lastName"}

    def test_confidence_extracted(self):
        r = SDKResult.from_operation(self._make_raw())
        assert r.confidence == pytest.approx(0.91)

    def test_filled_pdf_explicit_arg(self):
        r = SDKResult.from_operation(self._make_raw(), filled_pdf="/explicit/path.pdf")
        assert r.filled_pdf == "/explicit/path.pdf"

    def test_filled_pdf_from_pipeline_results(self):
        r = SDKResult.from_operation(self._make_raw())
        assert r.filled_pdf == "/tmp/filled.pdf"

    def test_stages_populated(self):
        r = SDKResult.from_operation(self._make_raw())
        assert set(r.stages.keys()) == {"extract", "map", "embed", "fill"}
        assert r.stages["extract"].ok is True
        assert r.stages["map"].output_file == "/tmp/map.json"

    def test_execution_time(self):
        r = SDKResult.from_operation(self._make_raw())
        assert r.execution_time == pytest.approx(10.0)

    def test_error_status(self):
        raw = self._make_raw(status="error", error="LLM quota exceeded")
        r = SDKResult.from_operation(raw)
        assert r.ok is False
        assert r.error == "LLM quota exceeded"

    def test_mapping_with_none_values_dropped(self):
        raw = self._make_raw()
        raw["pipeline_results"]["map"]["mapping"] = {"1": "firstName", "2": None}
        r = SDKResult.from_operation(raw)
        assert "2" not in r.mapping
        assert r.mapping == {"1": "firstName"}

    def test_empty_pipeline(self):
        r = SDKResult.from_operation({"status": "error", "error": "crashed"})
        assert r.ok is False
        assert r.stages == {}

    def test_embedded_pdf_defaults_to_none(self):
        r = SDKResult.from_operation(self._make_raw())
        assert r.embedded_pdf is None  # set explicitly by PDFMapper, not by from_operation


# ---------------------------------------------------------------------------
# SDKResult.save
# ---------------------------------------------------------------------------

class TestSDKResultSave:
    def test_save_copies_file(self, tmp_path):
        src = tmp_path / "filled.pdf"
        src.write_bytes(b"%PDF fake")
        dest = tmp_path / "output.pdf"

        r = SDKResult(status="success", filled_pdf=str(src))
        saved = r.save(str(dest))

        assert os.path.exists(saved)
        assert open(saved, "rb").read() == b"%PDF fake"

    def test_save_raises_when_no_filled_pdf(self):
        r = SDKResult.failure("failed")
        with pytest.raises(ValueError, match="No filled PDF"):
            r.save("/tmp/out.pdf")

    def test_save_raises_when_file_deleted(self, tmp_path):
        r = SDKResult(status="success", filled_pdf=str(tmp_path / "gone.pdf"))
        with pytest.raises(FileNotFoundError):
            r.save(str(tmp_path / "out.pdf"))


# ---------------------------------------------------------------------------
# SDKResult __str__
# ---------------------------------------------------------------------------

class TestSDKResultStr:
    def test_success_str(self):
        r = SDKResult(
            status="success",
            mapped_fields=8,
            total_fields=10,
            confidence=0.875,
            execution_time=12.3,
        )
        s = str(r)
        assert "success" in s
        assert "8/10" in s
        assert "88%" in s

    def test_error_str(self):
        r = SDKResult.failure("timeout")
        assert "error" in str(r)
        assert "timeout" in str(r)
