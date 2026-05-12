import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.db.enums import BadgeRuleType, UserRole
from app.models.story import StoryResponse


def _validate_password_strength(value: str) -> str:
    errors = []
    if not any(c.isupper() for c in value):
        errors.append("one uppercase letter")
    if not any(c.islower() for c in value):
        errors.append("one lowercase letter")
    if not any(c.isdigit() for c in value):
        errors.append("one digit")
    if not any(c in "!@#$%^&*()-_=+[]{}|;:',.<>?/`~" for c in value):
        errors.append("one special character")
    if errors:
        raise ValueError("Password must contain at least: " + ", ".join(errors))
    return value


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


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


class BadgeResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    icon_key: str
    rule_type: BadgeRuleType
    awarded_at: datetime

    model_config = {"from_attributes": True}


class UserProfileResponse(UserResponse):
    bio: str | None
    location: str | None
    avatar_url: str | None
    badges: list[BadgeResponse] = Field(default_factory=list)


class UserPublicProfileResponse(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str | None
    bio: str | None
    location: str | None
    avatar_url: str | None
    badges: list[BadgeResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    bio: str | None = None
    location: str | None = Field(default=None, max_length=255)

    @field_validator("display_name", "bio", "location", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)


class UserPasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserStoryListResponse(BaseModel):
    stories: list[StoryResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class UserEngagementStatsResponse(BaseModel):
    total_stories: int = Field(ge=0)
    total_likes_received: int = Field(ge=0)
    total_comments_received: int = Field(ge=0)
    total_saves_received: int = Field(ge=0)
    total_views_received: int = Field(ge=0)


class UserDashboardResponse(BaseModel):
    stories_count: int = Field(ge=0)
    saved_count: int = Field(ge=0)
    total_likes_received: int = Field(ge=0)
    total_comments_received: int = Field(ge=0)
    total_saves_received: int = Field(ge=0)
    total_views_received: int = Field(ge=0)
