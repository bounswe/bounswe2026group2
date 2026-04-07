from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.db.user import User
from app.models.user import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.auth_service import login_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
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
    responses={
        401: {"description": "Invalid email or password"},
    },
)
async def login(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    return await login_user(db, payload)


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"description": "Missing, invalid, or expired token"},
    },
)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
