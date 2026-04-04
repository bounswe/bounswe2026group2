from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.user import User
from app.models.user import UserRegisterRequest, UserResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


async def register_user(
    db: AsyncSession, payload: UserRegisterRequest
) -> UserResponse:
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
