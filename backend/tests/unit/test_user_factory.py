from app.db.enums import UserRole
from app.services.auth_service import verify_password
from tests.factories.user_factory import (
    make_login_payload,
    make_user_entity,
    make_user_payload,
)


def test_make_user_payload_defaults_are_valid():
    payload = make_user_payload()

    assert payload["username"] == "testuser"
    assert payload["email"] == "test@example.com"
    assert payload["password"] == "ValidPass1!"
    assert payload["display_name"] == "Test User"


def test_make_user_payload_overrides_and_suffix():
    payload = make_user_payload(
        username="alice",
        email="alice@example.com",
        password="AlicePass1!",
        display_name=None,
        suffix=7,
    )

    assert payload["username"] == "alice7"
    assert payload["email"] == "alice+7@example.com"
    assert payload["password"] == "AlicePass1!"
    assert "display_name" not in payload


def test_make_login_payload_defaults_and_suffix():
    default_payload = make_login_payload()
    suffix_payload = make_login_payload(email="login@example.com", password="AnyPass1!", suffix="x")

    assert default_payload == {"email": "test@example.com", "password": "ValidPass1!"}
    assert suffix_payload == {"email": "login+x@example.com", "password": "AnyPass1!"}


def test_make_user_entity_defaults_and_role_override():
    user = make_user_entity()
    admin = make_user_entity(
        username="admin",
        email="admin@example.com",
        password="AdminPass1!",
        role=UserRole.ADMIN,
        suffix=2,
    )

    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.role == UserRole.USER
    assert user.is_active is True
    assert user.password_hash != "ValidPass1!"
    assert verify_password("ValidPass1!", user.password_hash)

    assert admin.username == "admin2"
    assert admin.email == "admin+2@example.com"
    assert admin.role == UserRole.ADMIN
    assert verify_password("AdminPass1!", admin.password_hash)
