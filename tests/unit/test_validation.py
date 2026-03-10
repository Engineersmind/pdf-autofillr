# tests/unit/test_validation.py
import pytest
from chatbot.validation.phone_validator import validate_phone, normalise_phone
from chatbot.validation.field_validator import validate_field


class TestPhoneValidator:
    @pytest.mark.parametrize("phone,expected", [
        ("+1 212 555 1234", True),
        ("+44 20 7946 0958", True),
        ("212-555-1234", True),
        ("abc", False),
        ("", False),
        ("12", False),
    ])
    def test_validate_phone(self, phone, expected):
        assert validate_phone(phone) == expected

    def test_normalise_phone(self):
        assert normalise_phone("  +1  212  555 1234  ") == "+1 212 555 1234"


class TestFieldValidator:
    def test_valid_email(self):
        ok, _ = validate_field("investor_email_id", "alice@example.com")
        assert ok

    def test_invalid_email(self):
        ok, msg = validate_field("investor_email_id", "not-an-email")
        assert not ok
        assert "email" in msg.lower()

    def test_valid_phone(self):
        ok, _ = validate_field("investor_telephone_id", "+1 212 555 1234")
        assert ok

    def test_invalid_phone(self):
        ok, msg = validate_field("investor_telephone_id", "abc")
        assert not ok

    def test_empty_value(self):
        ok, msg = validate_field("investor_full_legal_name_id", "")
        assert not ok

    def test_none_value(self):
        ok, _ = validate_field("investor_full_legal_name_id", None)
        assert not ok
