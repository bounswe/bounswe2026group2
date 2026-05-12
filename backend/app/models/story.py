import uuid
from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.orm.attributes import NO_VALUE

from app.db.enums import DatePrecision, MediaType, ReportReason, ReportStatus, StoryStatus, StoryVisibility


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class StoryDateInput(BaseModel):
    date_start: int | date | None = Field(
        default=None,
        description="Start value. Either year (e.g. 1453) or ISO date (YYYY-MM-DD).",
    )
    date_end: int | date | None = Field(
        default=None,
        description="End value. Must match date_start type when provided.",
    )
    date_precision: DatePrecision | None = Field(
        default=None,
        description="Optional precision hint: 'year' or 'date'. Inferred from input type when omitted.",
    )

    @model_validator(mode="after")
    def check_date_input(self) -> Self:
        if self.date_start is None and self.date_end is None:
            if self.date_precision is not None:
                raise ValueError("date_precision requires date_start/date_end")
            return self

        if self.date_start is None and self.date_end is not None:
            raise ValueError("date_start is required when date_end is provided")

        if isinstance(self.date_start, int):
            if not 1 <= self.date_start <= 9999:
                raise ValueError("year input must be in range 1..9999")

            if self.date_end is not None and not isinstance(self.date_end, int):
                raise ValueError("date_start and date_end must use the same type")

            if isinstance(self.date_end, int):
                if not 1 <= self.date_end <= 9999:
                    raise ValueError("year input must be in range 1..9999")
                if self.date_end < self.date_start:
                    raise ValueError("date_end must be greater than or equal to date_start")

            if self.date_precision not in (None, DatePrecision.YEAR):
                raise ValueError("date_precision must be 'year' for year inputs")
            return self

        if self.date_end is not None and not isinstance(self.date_end, date):
            raise ValueError("date_start and date_end must use the same type")

        if isinstance(self.date_end, date) and self.date_end < self.date_start:
            raise ValueError("date_end must be greater than or equal to date_start")

        if self.date_precision not in (None, DatePrecision.DATE):
            raise ValueError("date_precision must be 'date' for date inputs")

        return self

    def normalize_date_range(self) -> tuple[date | None, date | None, DatePrecision | None]:
        if self.date_start is None:
            return None, None, None

        if isinstance(self.date_start, int):
            end_year = self.date_end if isinstance(self.date_end, int) else self.date_start
            return (
                date(self.date_start, 1, 1),
                date(end_year, 12, 31),
                DatePrecision.YEAR,
            )

        end_date = self.date_end if isinstance(self.date_end, date) else self.date_start
        return self.date_start, end_date, DatePrecision.DATE


class LocationInput(BaseModel):
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    label: str | None = Field(default=None, max_length=255)


class StoryCreateRequest(StoryDateInput):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    summary: str | None = None
    tags: list[str] | None = None
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    place_name: str | None = Field(default=None, max_length=255)
    is_anonymous: bool = False
    locations: list[LocationInput] | None = None


class StoryUpdateRequest(StoryDateInput):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    summary: str | None = None
    tags: list[str] | None = None
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    place_name: str | None = Field(default=None, max_length=255)
    is_anonymous: bool | None = None
    locations: list[LocationInput] | None = None


class StoryBoundsFilter(BaseModel):
    min_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    max_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    min_lng: float | None = Field(default=None, ge=-180.0, le=180.0)
    max_lng: float | None = Field(default=None, ge=-180.0, le=180.0)

    @model_validator(mode="after")
    def check_bounds(self) -> "StoryBoundsFilter":
        values = [self.min_lat, self.max_lat, self.min_lng, self.max_lng]
        provided_count = sum(v is not None for v in values)

        if provided_count not in (0, 4):
            raise ValueError("min_lat, max_lat, min_lng, max_lng must be provided together")

        if provided_count == 4:
            if self.min_lat > self.max_lat:
                raise ValueError("min_lat must be less than or equal to max_lat")
            if self.min_lng > self.max_lng:
                raise ValueError("min_lng must be less than or equal to max_lng")

        return self


class StoryDateRangeFilter(BaseModel):
    query_start: int | date | None = Field(default=None)
    query_end: int | date | None = Field(default=None)
    query_precision: DatePrecision | None = Field(default=None)

    def normalize_query_range(self) -> tuple[date | None, date | None, DatePrecision | None]:
        return StoryDateInput(
            date_start=self.query_start,
            date_end=self.query_end,
            date_precision=self.query_precision,
        ).normalize_date_range()


class LocationResponse(BaseModel):
    id: uuid.UUID
    latitude: float
    longitude: float
    label: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class StoryResponse(BaseModel):
    id: uuid.UUID
    title: str
    summary: str | None
    content: str
    tags: list[str] = Field(default_factory=list)
    author: str | None
    is_anonymous: bool
    place_name: str | None
    latitude: float | None
    longitude: float | None
    locations: list[LocationResponse] = Field(default_factory=list)
    date_start: date | None
    date_end: date | None
    date_precision: DatePrecision | None
    date_label: str | None
    status: StoryStatus
    visibility: StoryVisibility
    view_count: int = Field(default=0, ge=0)
    created_at: datetime

    model_config = {"from_attributes": True}

    @staticmethod
    def _extract_loaded_tag_names(story: object) -> list[str]:
        try:
            inspected_story = sa_inspect(story)
        except NoInspectionAvailable:
            tags = getattr(story, "tags", [])
            return [tag.name for tag in tags]

        tags_attr = inspected_story.attrs.tags
        if tags_attr.loaded_value is NO_VALUE:
            return []

        return [tag.name for tag in tags_attr.loaded_value]

    @staticmethod
    def _extract_loaded_locations(story: object) -> list[LocationResponse]:
        try:
            inspected_story = sa_inspect(story)
        except NoInspectionAvailable:
            locs = getattr(story, "locations", [])
            return [LocationResponse.model_validate(loc, from_attributes=True) for loc in locs]

        locations_attr = inspected_story.attrs.locations
        if locations_attr.loaded_value is NO_VALUE:
            return []

        return [LocationResponse.model_validate(loc, from_attributes=True) for loc in locations_attr.loaded_value]

    @classmethod
    def from_orm_with_author(cls, story: object, author_username: str) -> "StoryResponse":
        date_start = getattr(story, "date_start", None)
        date_end = getattr(story, "date_end", None)
        date_precision = getattr(story, "date_precision", None)

        if date_start and date_end and date_precision == DatePrecision.YEAR:
            if date_start.year == date_end.year:
                date_label = str(date_start.year)
            else:
                date_label = f"{date_start.year} - {date_end.year}"
        elif date_start and date_end:
            if date_start == date_end:
                date_label = date_start.isoformat()
            else:
                date_label = f"{date_start.isoformat()} - {date_end.isoformat()}"
        elif date_start:
            date_label = str(date_start.year) if date_precision == DatePrecision.YEAR else date_start.isoformat()
        else:
            date_label = None

        is_anonymous = getattr(story, "is_anonymous", False)
        tags = cls._extract_loaded_tag_names(story)
        locations = cls._extract_loaded_locations(story)

        return cls(
            id=story.id,
            title=story.title,
            summary=story.summary,
            content=story.content,
            tags=tags,
            author=None if is_anonymous else author_username,
            is_anonymous=is_anonymous,
            place_name=story.place_name,
            latitude=story.latitude,
            longitude=story.longitude,
            locations=locations,
            date_start=date_start,
            date_end=date_end,
            date_precision=date_precision,
            date_label=date_label,
            status=story.status,
            visibility=story.visibility,
            view_count=getattr(story, "view_count", None) or 0,
            created_at=story.created_at,
        )


class StoryListResponse(BaseModel):
    stories: list[StoryResponse]
    total: int


class MediaUploadRequest(BaseModel):
    media_type: MediaType
    alt_text: str | None = Field(default=None, max_length=500)
    caption: str | None = Field(default=None, max_length=500)
    transcript: str | None = None
    sort_order: int = Field(default=0, ge=0)

    @field_validator("transcript", mode="before")
    @classmethod
    def normalize_transcript(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)


class MediaFileResponse(BaseModel):
    id: uuid.UUID
    story_id: uuid.UUID
    bucket_name: str
    storage_key: str
    media_url: str
    original_filename: str
    mime_type: str
    media_type: MediaType
    file_size_bytes: int
    sort_order: int
    alt_text: str | None
    caption: str | None
    transcript: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MediaUploadResponse(BaseModel):
    media: MediaFileResponse


class StorySaveResponse(BaseModel):
    story_id: uuid.UUID
    saved: bool


class StoryLikeResponse(BaseModel):
    story_id: uuid.UUID
    liked: bool
    like_count: int = Field(default=0, ge=0)


class StoryDetailResponse(StoryResponse):
    media_files: list[MediaFileResponse] = Field(default_factory=list)
    like_count: int = Field(default=0, ge=0)
    new_badge: str | None = None


class StoryReportRequest(BaseModel):
    reason: ReportReason
    description: str | None = Field(default=None, max_length=1000)


class StoryReportResponse(BaseModel):
    id: uuid.UUID
    story_id: uuid.UUID
    user_id: uuid.UUID
    reason: ReportReason
    description: str | None
    status: ReportStatus
    created_at: datetime

    model_config = {"from_attributes": True}
