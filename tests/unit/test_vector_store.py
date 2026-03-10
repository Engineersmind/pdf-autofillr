# tests/unit/test_vector_store.py
import pytest
import tempfile
import os
from ragpdf.vector_stores.local_vector_store import LocalVectorStore


@pytest.fixture
def store(tmp_path):
    return LocalVectorStore(path=str(tmp_path / "vectors" / "vector_db.json"))


def make_embedding(val: float, dim: int = 4) -> list:
    return [val] * dim


def test_empty_store_returns_no_match(store):
    match = store.find_similar([0.1, 0.2, 0.3, 0.4], threshold=0.75, top_k=5)
    assert not match.matched
    assert match.confidence == 0.0


def test_add_and_find_vector(store):
    embedding = make_embedding(1.0)
    store.add_vector("investor_name", "Name field", "Identity", ["Investor"], embedding, initial_confidence=0.75)
    store.save()

    match = store.find_similar(make_embedding(1.0), threshold=0.75, top_k=5)
    assert match.matched
    assert match.field_name == "investor_name"
    assert match.confidence >= 0.99


def test_below_threshold_no_match(store):
    store.add_vector("investor_name", "", "", [], make_embedding(1.0))
    match = store.find_similar(make_embedding(0.0), threshold=0.75, top_k=5)
    assert not match.matched
    assert match.best_candidate == "investor_name"


def test_confidence_boost(store):
    vid = store.add_vector("investor_name", "", "", [], make_embedding(1.0), initial_confidence=0.75)
    new_conf = store.update_confidence(vid, is_positive=True, growth_rate=1.05, max_confidence=0.99)
    assert new_conf == pytest.approx(0.75 * 1.05, abs=1e-4)


def test_confidence_decay(store):
    vid = store.add_vector("investor_name", "", "", [], make_embedding(1.0), initial_confidence=0.75)
    new_conf = store.update_confidence(vid, is_positive=False, decay_rate=0.95, min_confidence=0.50)
    assert new_conf == pytest.approx(0.75 * 0.95, abs=1e-4)


def test_confidence_clamped_to_min(store):
    vid = store.add_vector("investor_name", "", "", [], make_embedding(1.0), initial_confidence=0.51)
    for _ in range(100):
        new_conf = store.update_confidence(vid, is_positive=False, decay_rate=0.95, min_confidence=0.50)
    assert new_conf >= 0.50


def test_confidence_clamped_to_max(store):
    vid = store.add_vector("investor_name", "", "", [], make_embedding(1.0), initial_confidence=0.98)
    for _ in range(100):
        new_conf = store.update_confidence(vid, is_positive=True, growth_rate=1.05, max_confidence=0.99)
    assert new_conf <= 0.99


def test_update_nonexistent_vector_returns_none(store):
    result = store.update_confidence("vec_999", is_positive=True)
    assert result is None


def test_top_k_results(store):
    for i in range(5):
        store.add_vector(f"field_{i}", "", "", [], make_embedding(float(i) / 10.0))
    match = store.find_similar(make_embedding(0.4), threshold=0.0, top_k=3)
    assert len(match.top_k) == 3


def test_persist_and_reload(tmp_path):
    path = str(tmp_path / "vec_db.json")
    store1 = LocalVectorStore(path=path)
    store1.add_vector("investor_name", "context", "section", ["h1"], make_embedding(1.0))
    store1.save()

    store2 = LocalVectorStore(path=path)
    assert store2.total_vectors() == 1
    assert store2.get_all_vectors()[0]["field_name"] == "investor_name"


def test_total_vectors(store):
    assert store.total_vectors() == 0
    store.add_vector("f1", "", "", [], make_embedding(1.0))
    store.add_vector("f2", "", "", [], make_embedding(0.5))
    assert store.total_vectors() == 2
