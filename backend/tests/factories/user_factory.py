from app.db.enums import UserRole
from app.db.user import User
from app.services.auth_service import hash_password


DEFAULT_USERNAME = "testuser"
DEFAULT_EMAIL = "test@example.com"
DEFAULT_PASSWORD = "ValidPass1!"
DEFAULT_DISPLAY_NAME = "Test User"


def make_user_payload(
    *,
    username: str = DEFAULT_USERNAME,
    email: str = DEFAULT_EMAIL,
    password: str = DEFAULT_PASSWORD,
    display_name: str | None = DEFAULT_DISPLAY_NAME,
) -> dict:
    payload = {
        "username": username,
        "email": email,
        "password": password,
    }
    if display_name is not None:
        payload["display_name"] = display_name
    return payload


def make_login_payload(
    *,
    email: str = DEFAULT_EMAIL,
    password: str = DEFAULT_PASSWORD,
) -> dict:
    return {
        "email": email,
        "password": password,
    }


def make_user_entity(
    *,
    username: str = DEFAULT_USERNAME,
    email: str = DEFAULT_EMAIL,
    password: str = DEFAULT_PASSWORD,
    role: UserRole = UserRole.USER,
    display_name: str | None = DEFAULT_DISPLAY_NAME,
    bio: str | None = None,
    is_active: bool = True,
    password_hash: str | None = None,
) -> User:
    return User(
        username=username,
        email=email,
        password_hash=password_hash or hash_password(password),
        display_name=display_name,
        bio=bio,
        role=role,
        is_active=is_active,
    )
