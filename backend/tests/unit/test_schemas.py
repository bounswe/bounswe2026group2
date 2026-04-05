import pytest
from pydantic import ValidationError

from app.models.user import UserRegisterRequest, UserLoginRequest


class TestUserRegisterRequestSchema:
    def test_valid_payload(self):
        req = UserRegisterRequest(
            username="john", email="john@example.com", password="MyPass1!"
        )
        assert req.username == "john"
        assert req.email == "john@example.com"

    def test_username_too_short(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                username="ab", email="a@b.com", password="MyPass1!"
            )

    def test_username_too_long(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                username="a" * 51, email="a@b.com", password="MyPass1!"
            )

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                username="john", email="not-an-email", password="MyPass1!"
            )

    def test_display_name_optional(self):
        req = UserRegisterRequest(
            username="john", email="john@example.com", password="MyPass1!"
        )
        assert req.display_name is None

    def test_display_name_provided(self):
        req = UserRegisterRequest(
            username="john",
            email="john@example.com",
            password="MyPass1!",
            display_name="John Doe",
        )
        assert req.display_name == "John Doe"


class TestUserLoginRequestSchema:
    def test_valid_payload(self):
        req = UserLoginRequest(email="john@example.com", password="anypass")
        assert req.email == "john@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            UserLoginRequest(email="bad", password="anypass")
