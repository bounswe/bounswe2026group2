from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
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
from app.services.auth_service import (
    change_user_password,
    get_user_profile,
    login_user,
    register_user,
    update_user_profile,
    upload_user_avatar,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account. Returns the created user profile on success.",
    responses={
        409: {"description": "Email or username already taken"},
        422: {"description": "Validation error (weak password, invalid email, etc.)"},
    },
)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    return await register_user(db, payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and obtain a JWT",
    description="Authenticate with email and password. Returns a Bearer JWT valid for 30 minutes.",
    responses={
        401: {"description": "Invalid email or password"},
        422: {"description": "Validation error (missing or malformed fields)"},
    },
)
async def login(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    return await login_user(db, payload)


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description="Return the profile of the authenticated user. Requires a valid Bearer token.",
    responses={
        401: {"description": "Missing, invalid, or expired token"},
    },
)
async def me(current_user: User = Depends(get_current_user)):
    return get_user_profile(current_user)


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    summary="Update current user profile",
    description="Update profile fields used by the edit profile page. Requires a valid Bearer token.",
    responses={
        401: {"description": "Missing, invalid, or expired token"},
        422: {"description": "Validation error for profile fields"},
    },
)
async def update_me(
    payload: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await update_user_profile(db, current_user, payload)


@router.post(
    "/me/avatar",
    response_model=UserProfileResponse,
    summary="Upload current user avatar",
    description="Upload a profile image for the authenticated user. Requires a valid Bearer token.",
    responses={
        401: {"description": "Missing, invalid, or expired token"},
        413: {"description": "Avatar file exceeds the upload size limit"},
        422: {"description": "Unsupported avatar file type"},
        502: {"description": "Object storage backend unavailable"},
    },
)
async def upload_me_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await upload_user_avatar(db, current_user, file)


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change current user password",
    description="Change the authenticated user's password after validating the current password.",
    responses={
        400: {"description": "Current password is incorrect"},
        401: {"description": "Missing, invalid, or expired token"},
        422: {"description": "Validation error for the new password"},
    },
)
async def change_me_password(
    payload: UserPasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await change_user_password(db, current_user, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
