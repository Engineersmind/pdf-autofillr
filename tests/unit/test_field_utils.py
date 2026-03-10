# tests/unit/test_field_utils.py
from chatbot.utils.field_utils import (
    get_missing_mandatory_keys,
    get_optional_fields,
    classify_fields_by_type,
    format_field_name,
)
from chatbot.utils.dict_utils import flatten_dict, unflatten_dict, deep_update
from chatbot.utils.address_utils import is_address_field, copy_registered_to_mailing
from chatbot.utils.intent_detection import is_skip_intent, is_affirmative, is_negative


class TestDictUtils:
    def test_flatten(self):
        d = {"a": {"b": {"c": 1}}}
        assert flatten_dict(d) == {"a.b.c": 1}

    def test_unflatten(self):
        d = {"a.b.c": 1}
        assert unflatten_dict(d) == {"a": {"b": {"c": 1}}}

    def test_roundtrip(self):
        original = {"identity": {"name": "Alice", "email": "a@b.com"}}
        assert unflatten_dict(flatten_dict(original)) == original

    def test_deep_update(self):
        base = {"a": {"x": 1, "y": 2}}
        update = {"a": {"y": 99, "z": 3}}
        result = deep_update(base, update)
        assert result == {"a": {"x": 1, "y": 99, "z": 3}}


class TestFieldUtils:
    def test_missing_mandatory(self):
        live = {"name_id": "Alice", "email_id": ""}
        mandatory = {"name_id": "", "email_id": ""}
        missing = get_missing_mandatory_keys(live, mandatory)
        assert "email_id" in missing
        assert "name_id" not in missing

    def test_classify_fields(self):
        meta = {"investor_type": {"individual_check": {"type": "boolean"}}}
        booleans, texts = classify_fields_by_type(
            ["investor_type.individual_check", "investor_email_id"], meta
        )
        assert "investor_type.individual_check" in booleans
        assert "investor_email_id" in texts

    def test_format_field_name(self):
        # format_field_name takes the last segment of the dotted path,
        # strips _id/_check suffixes, and title-cases it.
        # "identity.investor_full_legal_name_id" → last segment "investor_full_legal_name_id"
        # → strip "_id" → "investor_full_legal_name" → title → "Investor Full Legal Name"
        assert format_field_name("identity.investor_full_legal_name_id") == "Investor Full Legal Name"
        assert format_field_name("investor_email_id") == "Investor Email"
        assert format_field_name("address_registered.address_registered_city_id") == "Address Registered City"


class TestAddressUtils:
    def test_is_address_field(self):
        ok, addr_type, sub = is_address_field("address_registered.address_registered_city_id")
        assert ok
        assert addr_type == "registered"
        assert sub == "city"

    def test_copy_registered_to_mailing(self):
        live = {
            "address_registered.address_registered_city_id": "New York",
            "address_mailing.address_mailing_city_id": "",
        }
        copied = copy_registered_to_mailing(live)
        assert live["address_mailing.address_mailing_city_id"] == "New York"
        assert "address_mailing.address_mailing_city_id" in copied


class TestIntentDetection:
    def test_skip(self):
        assert is_skip_intent("skip")
        assert is_skip_intent("N/A")
        assert not is_skip_intent("John Doe")

    def test_affirmative(self):
        assert is_affirmative("yes")
        assert is_affirmative("YES")
        assert not is_affirmative("no")

    def test_negative(self):
        assert is_negative("no")
        assert not is_negative("yes")