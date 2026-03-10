# tests/unit/test_storage_local.py
import pytest
import json
from ragpdf.storage.local_storage import LocalStorage


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(data_path=str(tmp_path))


def test_save_and_load_json(storage):
    data = {"key": "value", "num": 42}
    storage.save_json("test/data.json", data)
    loaded = storage.load_json("test/data.json")
    assert loaded == data


def test_load_missing_key_returns_none(storage):
    assert storage.load_json("nonexistent/file.json") is None


def test_append_and_load_jsonl(storage):
    storage.append_jsonl("logs/events.jsonl", {"event": "a"})
    storage.append_jsonl("logs/events.jsonl", {"event": "b"})
    records = storage.load_jsonl("logs/events.jsonl")
    assert len(records) == 2
    assert records[0]["event"] == "a"
    assert records[1]["event"] == "b"


def test_load_missing_jsonl_returns_empty(storage):
    assert storage.load_jsonl("nonexistent/file.jsonl") == []


def test_overwrite_json(storage):
    storage.save_json("file.json", {"v": 1})
    storage.save_json("file.json", {"v": 2})
    assert storage.load_json("file.json")["v"] == 2


def test_nested_paths_created(storage, tmp_path):
    storage.save_json("a/b/c/d/file.json", {"x": 1})
    assert (tmp_path / "a" / "b" / "c" / "d" / "file.json").exists()


def test_exists(storage):
    assert not storage.exists("test/file.json")
    storage.save_json("test/file.json", {})
    assert storage.exists("test/file.json")


# ── tests/unit/test_helpers.py ────────────────────────────────────────────────

from ragpdf.utils.helpers import (
    generate_submission_id, generate_vector_id,
    get_pdf_frequency, safe_divide, calculate_avg,
)


def test_submission_id_format():
    sid = generate_submission_id("user1", "sess1", "pdf1", 1)
    parts = sid.split("__")
    assert parts[0] == "user1"
    assert parts[1] == "sess1"
    assert parts[2] == "pdf1"
    assert parts[3] == "f1"


def test_generate_vector_id_empty():
    assert generate_vector_id([]) == "vec_001"


def test_generate_vector_id_sequential():
    existing = [{"vector_id": "vec_003"}, {"vector_id": "vec_007"}]
    assert generate_vector_id(existing) == "vec_008"


def test_get_pdf_frequency_new():
    assert get_pdf_frequency("abc123", {}) == 1
    assert get_pdf_frequency("abc123", None) == 1


def test_get_pdf_frequency_existing():
    mapping = {"abc123": {"total_submissions": 4}}
    assert get_pdf_frequency("abc123", mapping) == 5


def test_safe_divide():
    assert safe_divide(10, 5) == 2.0
    assert safe_divide(10, 0) == 0.0
    assert safe_divide(10, 0, default=-1.0) == -1.0


def test_calculate_avg():
    assert calculate_avg([1.0, 2.0, 3.0]) == 2.0
    assert calculate_avg([]) == 0.0


# ── tests/unit/test_metrics_service.py ───────────────────────────────────────

from ragpdf.services.metrics_service import MetricsService


@pytest.fixture
def metrics_service():
    return MetricsService()


def _make_preds(fields, predicted=True, confidence=0.9):
    return {
        "predictions": {
            f["field_id"]: {"predicted_field_name": f"mapped_{f['field_id']}", "confidence": confidence}
            if predicted else None
            for f in fields
        }
    }


def _make_final(fields, selected_from="rag"):
    return {
        "final_predictions": {
            f["field_id"]: {
                "selected_field_name": f"mapped_{f['field_id']}",
                "selected_from": selected_from,
                f"{selected_from}_confidence": 0.9,
            }
            for f in fields
        }
    }


def _make_case_cls(fields):
    from ragpdf.utils.constants import CASE_A, CASE_B, CASE_C, CASE_D, CASE_E
    return {
        "total_fields": len(fields),
        "case_breakdown": {
            CASE_A: {"count": len(fields), "field_ids": [f["field_id"] for f in fields]},
            CASE_B: {"count": 0, "field_ids": []},
            CASE_C: {"count": 0, "field_ids": []},
            CASE_D: {"count": 0, "field_ids": []},
            CASE_E: {"count": 0, "field_ids": []},
        }
    }


def test_metrics_initial_accuracy_is_1(metrics_service):
    fields = [{"field_id": "f1"}, {"field_id": "f2"}]
    metrics = metrics_service.calculate_metrics(
        user_id="u1", session_id="s1", pdf_id="p1",
        submission_id="sub1", pdf_hash="hash1",
        rag_preds=_make_preds(fields),
        llm_preds=_make_preds(fields),
        final_preds=_make_final(fields),
        case_classification=_make_case_cls(fields),
        pdf_category={"category": "PE", "sub_category": "LP", "document_type": "Sub"},
    )
    assert metrics["accuracy"]["accuracy_ensemble"] == 1.0
    assert metrics["accuracy"]["accuracy_rag"] == 1.0


def test_metrics_recalculate_after_errors(metrics_service):
    fields = [{"field_id": "f1"}, {"field_id": "f2"}]
    metrics = metrics_service.calculate_metrics(
        user_id="u1", session_id="s1", pdf_id="p1",
        submission_id="sub1", pdf_hash="hash1",
        rag_preds=_make_preds(fields),
        llm_preds=_make_preds(fields),
        final_preds=_make_final(fields, "rag"),
        case_classification=_make_case_cls(fields),
        pdf_category={"category": "PE", "sub_category": "LP", "document_type": "Sub"},
    )
    updated = metrics_service.recalculate_accuracy_after_errors(
        metrics=metrics,
        final_preds=_make_final(fields, "rag"),
        errors=[{"field_name": "mapped_f1"}],
    )
    assert updated["accuracy"]["errors_ensemble"] == 1
    assert updated["accuracy"]["accuracy_ensemble"] < 1.0
