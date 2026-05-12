from app.db.enums import UserRole
from app.db.user import User
from app.services.auth_service import hash_password

DEFAULT_USERNAME = "testuser"
DEFAULT_EMAIL = "test@example.com"
DEFAULT_PASSWORD = "ValidPass1!"
DEFAULT_DISPLAY_NAME = "Test User"


def _with_suffix(base_value: str, suffix: int | str | None) -> str:
    if suffix is None:
        return base_value
    return f"{base_value}{suffix}"


def _email_with_suffix(base_email: str, suffix: int | str | None) -> str:
    if suffix is None:
        return base_email
    local, at, domain = base_email.partition("@")
    if at:
        return f"{local}+{suffix}@{domain}"
    return f"{base_email}{suffix}"


def make_user_payload(
    *,
    username: str = DEFAULT_USERNAME,
    email: str = DEFAULT_EMAIL,
    password: str = DEFAULT_PASSWORD,
    display_name: str | None = DEFAULT_DISPLAY_NAME,
    suffix: int | str | None = None,
) -> dict:
    username = _with_suffix(username, suffix)
    email = _email_with_suffix(email, suffix)
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
    suffix: int | str | None = None,
) -> dict:
    email = _email_with_suffix(email, suffix)
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
    location: str | None = None,
    avatar_bucket_name: str | None = None,
    avatar_storage_key: str | None = None,
    is_active: bool = True,
    is_restricted: bool = False,
    password_hash: str | None = None,
    suffix: int | str | None = None,
) -> User:
    username = _with_suffix(username, suffix)
    email = _email_with_suffix(email, suffix)
    return User(
        username=username,
        email=email,
        password_hash=password_hash or hash_password(password),
        display_name=display_name,
        bio=bio,
        location=location,
        avatar_bucket_name=avatar_bucket_name,
        avatar_storage_key=avatar_storage_key,
        role=role,
        is_active=is_active,
        is_restricted=is_restricted,
    )
