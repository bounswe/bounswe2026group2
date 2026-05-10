import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import HTTPException, UploadFile, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.enums import MediaType
from app.db.user import User
from app.models.user import (
    TokenResponse,
    UserLoginRequest,
    UserPasswordChangeRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.storage import build_public_object_url, delete_object, get_bucket_for_media_type, upload_bytes

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_AVATAR_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
ALLOWED_AVATAR_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
AVATAR_MIME_TYPE_ALIASES = {"image/jpg": "image/jpeg"}
GENERIC_BINARY_MIME_TYPES = {"application/octet-stream", "binary/octet-stream"}
AVATAR_MIME_TYPE_FALLBACKS_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def get_user_profile(user: User) -> UserProfileResponse:
    avatar_url = None
    if user.avatar_bucket_name and user.avatar_storage_key:
        avatar_url = build_public_object_url(
            bucket_name=user.avatar_bucket_name,
            storage_key=user.avatar_storage_key,
        )

    return UserProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        bio=user.bio,
        location=user.location,
        avatar_url=avatar_url,
        role=user.role,
        created_at=user.created_at,
    )


def _normalize_avatar_content_type(file: UploadFile) -> str:
    raw_content_type = (file.content_type or "").split(";")[0].strip().lower()
    normalized_content_type = AVATAR_MIME_TYPE_ALIASES.get(raw_content_type, raw_content_type)
    if normalized_content_type in GENERIC_BINARY_MIME_TYPES:
        extension = Path(file.filename or "").suffix.lower()
        fallback_content_type = AVATAR_MIME_TYPE_FALLBACKS_BY_EXTENSION.get(extension)
        if fallback_content_type:
            return fallback_content_type
    return normalized_content_type


def _validate_avatar_upload(file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content type is required",
        )

    normalized_content_type = _normalize_avatar_content_type(file)
    if normalized_content_type not in ALLOWED_AVATAR_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported avatar mime type '{normalized_content_type}'",
        )

    return normalized_content_type


def _build_avatar_storage_key(user_id: uuid.UUID, filename: str) -> str:
    extension = Path(filename).suffix.lower()
    return f"users/{user_id}/avatar/{uuid.uuid4()}{extension}"


async def register_user(db: AsyncSession, payload: UserRegisterRequest) -> UserResponse:
    email = payload.email.strip().lower()
    username = payload.username.strip()

    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check username uniqueness
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


async def login_user(db: AsyncSession, payload: UserLoginRequest) -> TokenResponse:
    email = payload.email.strip().lower()

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user)
    return TokenResponse(access_token=token)


async def update_user_profile(
    db: AsyncSession,
    current_user: User,
    payload: UserProfileUpdateRequest,
) -> UserProfileResponse:
    updated = False

    if "display_name" in payload.model_fields_set:
        current_user.display_name = payload.display_name
        updated = True
    if "bio" in payload.model_fields_set:
        current_user.bio = payload.bio
        updated = True
    if "location" in payload.model_fields_set:
        current_user.location = payload.location
        updated = True

    if updated:
        await db.commit()
        await db.refresh(current_user)

    return get_user_profile(current_user)


async def upload_user_avatar(
    db: AsyncSession,
    current_user: User,
    file: UploadFile,
) -> UserProfileResponse:
    normalized_content_type = _validate_avatar_upload(file)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(file_bytes) > MAX_AVATAR_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_AVATAR_UPLOAD_BYTES} bytes",
        )

    bucket_name = get_bucket_for_media_type(MediaType.IMAGE)
    storage_key = _build_avatar_storage_key(current_user.id, file.filename)

    try:
        upload_bytes(
            bucket_name=bucket_name,
            storage_key=storage_key,
            content=file_bytes,
            content_type=normalized_content_type,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload avatar to storage",
        )

    old_bucket_name = current_user.avatar_bucket_name
    old_storage_key = current_user.avatar_storage_key
    current_user.avatar_bucket_name = bucket_name
    current_user.avatar_storage_key = storage_key

    try:
        await db.commit()
        await db.refresh(current_user)
    except Exception:
        await db.rollback()
        try:
            delete_object(bucket_name=bucket_name, storage_key=storage_key)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist avatar metadata",
        )

    if old_bucket_name and old_storage_key:
        try:
            delete_object(bucket_name=old_bucket_name, storage_key=old_storage_key)
        except Exception:
            pass

    return get_user_profile(current_user)


async def change_user_password(
    db: AsyncSession,
    current_user: User,
    payload: UserPasswordChangeRequest,
) -> None:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = hash_password(payload.new_password)
    await db.commit()
