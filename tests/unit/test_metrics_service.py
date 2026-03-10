# tests/unit/test_metrics_service.py
import pytest
from unittest.mock import MagicMock
from ragpdf.services.metrics_service import MetricsService


@pytest.fixture
def svc():
    mock_storage = MagicMock()
    return MetricsService(mock_storage)


def _make_preds(n=5):
    rag = {"predictions": {f"f{i}": {"predicted_field_name": f"field_{i}", "confidence": 0.85} for i in range(n)}}
    llm = {"predictions": {f"f{i}": {"predicted_field_name": f"field_{i}", "confidence": 0.90} for i in range(n)}}
    fin = {"final_predictions": {f"f{i}": {"selected_field_name": f"field_{i}", "selected_from": "rag", "rag_confidence": 0.85} for i in range(n)}}
    return rag, llm, fin


def _make_cc(n=5):
    from ragpdf.utils.constants import CASE_A, CASE_B, CASE_C, CASE_D, CASE_E
    return {
        "total_fields": n,
        "case_breakdown": {
            CASE_A: {"count": n, "field_ids": [f"f{i}" for i in range(n)]},
            CASE_B: {"count": 0, "field_ids": []},
            CASE_C: {"count": 0, "field_ids": []},
            CASE_D: {"count": 0, "field_ids": []},
            CASE_E: {"count": 0, "field_ids": []},
        }
    }


def test_calculate_metrics_structure(svc):
    rag, llm, fin = _make_preds()
    cc = _make_cc()
    cat = {"category": "PE", "sub_category": "LP", "document_type": "Sub Agreement"}
    m = svc.calculate_metrics("u","s","p","sub_1","hash","rag",rag,llm,fin,cc,cat)
    assert "accuracy" in m
    assert "coverage" in m
    assert "field_counts" in m
    assert m["accuracy"]["accuracy_ensemble"] == 1.0
    assert m["field_counts"]["total_fields"] == 5


def test_coverage_calculation(svc):
    rag, llm, fin = _make_preds(4)
    cc = _make_cc(4)
    cat = {"category": "PE", "sub_category": "LP", "document_type": "Sub"}
    m = svc.calculate_metrics("u","s","p","sub_1","hash","rag",rag,llm,fin,cc,cat)
    assert m["coverage"]["coverage_ensemble"] == 1.0
