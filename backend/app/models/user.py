import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.db.enums import UserRole


class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        errors = []
        if not any(c.isupper() for c in v):
            errors.append("one uppercase letter")
        if not any(c.islower() for c in v):
            errors.append("one lowercase letter")
        if not any(c.isdigit() for c in v):
            errors.append("one digit")
        if not any(c in "!@#$%^&*()-_=+[]{}|;:',.<>?/`~" for c in v):
            errors.append("one special character")
        if errors:
            raise ValueError(
                "Password must contain at least: " + ", ".join(errors)
            )
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str



class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    display_name: str | None
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

