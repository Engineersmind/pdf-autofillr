"""Unit tests for schema_enforcer."""
from uploaddocument.transform.schema_enforcer import enforce_schema


SCHEMA = {
    "investor_name_id": "",
    "investor_email_id": "",
    "accredited_check": False,
    "address_registered": {
        "address_registered_city_id": "",
        "address_registered_country_id": "",
    },
}


def test_basic_extraction():
    raw = {"investor_name_id": "John", "investor_email_id": "j@x.com", "accredited_check": True}
    result = enforce_schema(raw, SCHEMA)
    assert result["investor_name_id"] == "John"
    assert result["accredited_check"] is True


def test_missing_fields_default_to_empty():
    result = enforce_schema({}, SCHEMA)
    assert result["investor_name_id"] == ""
    assert result["accredited_check"] is False


def test_nested_dict():
    raw = {"address_registered": {"address_registered_city_id": "New York"}}
    result = enforce_schema(raw, SCHEMA)
    assert result["address_registered"]["address_registered_city_id"] == "New York"
    assert result["address_registered"]["address_registered_country_id"] == ""


def test_bool_coercion_from_string():
    raw = {"accredited_check": "true"}
    result = enforce_schema(raw, SCHEMA)
    assert result["accredited_check"] is True


def test_none_becomes_empty():
    raw = {"investor_name_id": None}
    result = enforce_schema(raw, SCHEMA)
    assert result["investor_name_id"] == ""
