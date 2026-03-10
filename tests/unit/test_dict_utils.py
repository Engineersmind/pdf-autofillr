"""Unit tests for dict_utils."""
from uploaddocument.transform.dict_utils import flatten_dict, unflatten_dict, deep_update


def test_flatten_simple():
    d = {"a": {"b": {"c": "val"}}}
    assert flatten_dict(d) == {"a.b.c": "val"}


def test_flatten_mixed():
    d = {"name": "John", "address": {"city": "NY", "zip": "10001"}}
    flat = flatten_dict(d)
    assert flat["address.city"] == "NY"
    assert flat["name"] == "John"


def test_unflatten_roundtrip():
    original = {"investor.name": "Jane", "investor.email": "j@x.com"}
    nested = unflatten_dict(original)
    assert nested["investor"]["name"] == "Jane"


def test_deep_update():
    base = {"a": {"x": 1, "y": 2}, "b": 3}
    updates = {"a": {"y": 99, "z": 100}, "b": 999}
    result = deep_update(base, updates)
    assert result["a"]["x"] == 1
    assert result["a"]["y"] == 99
    assert result["b"] == 999
