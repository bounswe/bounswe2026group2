import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CommentAuthorResponse(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str | None = None


class CommentCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    id: uuid.UUID
    story_id: uuid.UUID
    content: str
    author: CommentAuthorResponse
    created_at: datetime
    updated_at: datetime


class CommentListResponse(BaseModel):
    comments: list[CommentResponse]
    total: int
