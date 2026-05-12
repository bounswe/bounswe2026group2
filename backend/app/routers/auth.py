import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
    build_google_auth_url,
    change_user_password,
    get_full_user_profile,
    google_oauth_login,
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
    "/google/login",
    summary="Initiate Google OAuth login",
    description="Redirects the user to Google's consent screen to begin the OAuth2 flow.",
    status_code=status.HTTP_302_FOUND,
    include_in_schema=True,
)
async def google_login(response: Response):
    state = secrets.token_urlsafe(32)
    redirect = RedirectResponse(url=build_google_auth_url(state))
    redirect.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        max_age=300,
    )
    return redirect


@router.get(
    "/google/callback",
    response_model=TokenResponse,
    summary="Google OAuth callback",
    description="Exchanges the authorization code from Google for a JWT. Creates a new account if the Google email is not yet registered.",
    responses={
        400: {"description": "Missing or mismatched OAuth state (CSRF check failed)"},
        401: {"description": "Code exchange or userinfo fetch failed"},
    },
)
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="CSRF state token returned by Google"),
    oauth_state: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not oauth_state or state != oauth_state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
    token = await google_oauth_login(db, code)
    fragment = urlencode({"access_token": token.access_token, "token_type": token.token_type})
    return RedirectResponse(url=f"{settings.FRONTEND_GOOGLE_CALLBACK_URL}#{fragment}")


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description="Return the profile of the authenticated user. Requires a valid Bearer token.",
    responses={
        401: {"description": "Missing, invalid, or expired token"},
    },
)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_full_user_profile(db, current_user)


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
