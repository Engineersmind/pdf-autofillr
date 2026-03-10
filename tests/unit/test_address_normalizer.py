"""Unit tests for address_normalizer."""
from uploaddocument.transform.address_normalizer import normalize_address, apply_address_normalization


def test_simple_split():
    l1, l2 = normalize_address("123 Main St, Apt 4B, New York, NY 10001")
    assert l1 == "123 Main St, Apt 4B"
    assert l2 == "New York, NY 10001"


def test_single_part():
    l1, l2 = normalize_address("123 Main Street")
    assert l1 == "123 Main Street"
    assert l2 == ""


def test_empty_string():
    l1, l2 = normalize_address("")
    assert l1 == ""
    assert l2 == ""


def test_apply_normalization():
    data = {
        "address_registered": {
            "address_registered_line1_id": "100 Wall St, Suite 200, New York, NY 10005",
            "address_registered_line2_id": "",
        }
    }
    result = apply_address_normalization(data)
    assert result["address_registered"]["address_registered_line1_id"] == "100 Wall St, Suite 200"
    assert result["address_registered"]["address_registered_line2_id"] == "New York, NY 10005"
