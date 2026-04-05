import pytest
from pydantic import ValidationError

from app.models.user import UserRegisterRequest


def _make_payload(**overrides):
    base = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "ValidPass1!",
    }
    base.update(overrides)
    return base


class TestPasswordStrengthValidation:
    def test_valid_password(self):
        req = UserRegisterRequest(**_make_payload(password="StrongPass1!"))
        assert req.password == "StrongPass1!"

    def test_missing_uppercase(self):
        with pytest.raises(ValidationError, match="one uppercase letter"):
            UserRegisterRequest(**_make_payload(password="weakpass1!"))

    def test_missing_lowercase(self):
        with pytest.raises(ValidationError, match="one lowercase letter"):
            UserRegisterRequest(**_make_payload(password="ALLCAPS1!"))

    def test_missing_digit(self):
        with pytest.raises(ValidationError, match="one digit"):
            UserRegisterRequest(**_make_payload(password="NoDigits!"))

    def test_missing_special_character(self):
        with pytest.raises(ValidationError, match="one special character"):
            UserRegisterRequest(**_make_payload(password="NoSpecial1"))

    def test_too_short(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(**_make_payload(password="Sh1!"))

    def test_multiple_missing(self):
        with pytest.raises(ValidationError, match="one uppercase letter") as exc_info:
            UserRegisterRequest(**_make_payload(password="nouppernodigit"))
        error_msg = str(exc_info.value)
        assert "one digit" in error_msg
        assert "one special character" in error_msg
