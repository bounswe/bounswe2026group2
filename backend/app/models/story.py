import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.db.enums import MediaType, StoryStatus, StoryVisibility


class StoryCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    summary: str | None = None
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    place_name: str | None = Field(default=None, max_length=255)
    date_start: int | None = Field(default=None, ge=1, le=9999)
    date_end: int | None = Field(default=None, ge=1, le=9999)

    @model_validator(mode="after")
    def check_date_range(self) -> "StoryCreateRequest":
        if self.date_start is not None and self.date_end is not None:
            if self.date_end < self.date_start:
                raise ValueError("date_end must be greater than or equal to date_start")
        return self


class StoryResponse(BaseModel):
    id: uuid.UUID
    title: str
    summary: str | None
    content: str
    author: str
    place_name: str | None
    latitude: float | None
    longitude: float | None
    date_start: int | None
    date_end: int | None
    date_label: str | None
    status: StoryStatus
    visibility: StoryVisibility
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_author(cls, story: object, author_username: str) -> "StoryResponse":
        date_start = getattr(story, "date_start", None)
        date_end = getattr(story, "date_end", None)

        if date_start and date_end:
            date_label = f"{date_start} - {date_end}"
        elif date_start:
            date_label = str(date_start)
        else:
            date_label = None

        return cls(
            id=story.id,
            title=story.title,
            summary=story.summary,
            content=story.content,
            author=author_username,
            place_name=story.place_name,
            latitude=story.latitude,
            longitude=story.longitude,
            date_start=date_start,
            date_end=date_end,
            date_label=date_label,
            status=story.status,
            visibility=story.visibility,
            created_at=story.created_at,
        )


class StoryListResponse(BaseModel):
    stories: list[StoryResponse]
    total: int


class MediaUploadRequest(BaseModel):
    media_type: MediaType
    alt_text: str | None = Field(default=None, max_length=500)
    caption: str | None = Field(default=None, max_length=500)
    sort_order: int = Field(default=0, ge=0)


class MediaFileResponse(BaseModel):
    id: uuid.UUID
    story_id: uuid.UUID
    bucket_name: str
    storage_key: str
    original_filename: str
    mime_type: str
    media_type: MediaType
    file_size_bytes: int
    sort_order: int
    alt_text: str | None
    caption: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MediaUploadResponse(BaseModel):
    media: MediaFileResponse
