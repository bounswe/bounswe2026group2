import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.db.enums import DatePrecision, MediaType, StoryStatus, StoryVisibility
from app.models.comment import CommentCreateRequest
from app.models.story import (
    MediaUploadRequest,
    StoryBoundsFilter,
    StoryCreateRequest,
    StoryDateRangeFilter,
    StoryResponse,
    StoryUpdateRequest,
)
from app.models.user import UserLoginRequest, UserRegisterRequest


class TestUserRegisterRequestSchema:
    def test_valid_payload(self):
        req = UserRegisterRequest(username="john", email="john@example.com", password="MyPass1!")
        assert req.username == "john"
        assert req.email == "john@example.com"

    def test_username_too_short(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(username="ab", email="a@b.com", password="MyPass1!")

    def test_username_too_long(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(username="a" * 51, email="a@b.com", password="MyPass1!")

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(username="john", email="not-an-email", password="MyPass1!")

    def test_display_name_optional(self):
        req = UserRegisterRequest(username="john", email="john@example.com", password="MyPass1!")
        assert req.display_name is None

    def test_display_name_provided(self):
        req = UserRegisterRequest(
            username="john",
            email="john@example.com",
            password="MyPass1!",
            display_name="John Doe",
        )
        assert req.display_name == "John Doe"


class TestUserLoginRequestSchema:
    def test_valid_payload(self):
        req = UserLoginRequest(email="john@example.com", password="anypass")
        assert req.email == "john@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            UserLoginRequest(email="bad", password="anypass")


class TestStoryDateSchemaValidation:
    def _base_story_payload(self) -> dict:
        return {
            "title": "Conquest of Constantinople",
            "content": "Historical event details",
            "summary": "A key turning point",
            "latitude": 41.0082,
            "longitude": 28.9784,
            "place_name": "Istanbul",
        }

    def test_create_accepts_valid_date_range(self):
        payload = self._base_story_payload() | {"date_start": 1400, "date_end": 1453}
        req = StoryCreateRequest(**payload)

        assert req.date_start == 1400
        assert req.date_end == 1453
        normalized_start, normalized_end, normalized_precision = req.normalize_date_range()
        assert normalized_start == date(1400, 1, 1)
        assert normalized_end == date(1453, 12, 31)
        assert normalized_precision == DatePrecision.YEAR

    def test_create_accepts_single_date_start_only(self):
        payload = self._base_story_payload() | {"date_start": 1453, "date_end": None}
        req = StoryCreateRequest(**payload)

        assert req.date_start == 1453
        assert req.date_end is None
        normalized_start, normalized_end, normalized_precision = req.normalize_date_range()
        assert normalized_start == date(1453, 1, 1)
        assert normalized_end == date(1453, 12, 31)
        assert normalized_precision == DatePrecision.YEAR

    def test_create_accepts_single_exact_date(self):
        payload = self._base_story_payload() | {"date_start": "1453-05-29"}
        req = StoryCreateRequest(**payload)

        normalized_start, normalized_end, normalized_precision = req.normalize_date_range()
        assert normalized_start == date(1453, 5, 29)
        assert normalized_end == date(1453, 5, 29)
        assert normalized_precision == DatePrecision.DATE

    def test_create_rejects_invalid_date_range(self):
        payload = self._base_story_payload() | {"date_start": 1453, "date_end": 1400}

        with pytest.raises(ValidationError, match="date_end must be greater than or equal to date_start"):
            StoryCreateRequest(**payload)

    @pytest.mark.parametrize("field_name, field_value", [("date_start", 0), ("date_end", 10000)])
    def test_create_rejects_out_of_bounds_dates(self, field_name: str, field_value: int):
        payload = self._base_story_payload() | {field_name: field_value}

        with pytest.raises(ValidationError):
            StoryCreateRequest(**payload)

    def test_create_rejects_mixed_type_range(self):
        payload = self._base_story_payload() | {
            "date_start": 1453,
            "date_end": "1453-05-29",
        }

        with pytest.raises(ValidationError, match="must use the same type"):
            StoryCreateRequest(**payload)

    def test_create_rejects_wrong_precision_for_date_inputs(self):
        payload = self._base_story_payload() | {
            "date_start": "1453-05-29",
            "date_precision": "year",
        }

        with pytest.raises(ValidationError, match="must be 'date'"):
            StoryCreateRequest(**payload)

    def test_update_accepts_valid_date_range(self):
        payload = self._base_story_payload() | {"date_start": 1900, "date_end": 1910}
        req = StoryUpdateRequest(**payload)

        assert req.date_start == 1900
        assert req.date_end == 1910

    def test_update_rejects_invalid_date_range(self):
        payload = self._base_story_payload() | {"date_start": 1910, "date_end": 1900}

        with pytest.raises(ValidationError, match="date_end must be greater than or equal to date_start"):
            StoryUpdateRequest(**payload)


class TestStoryDateRangeFilter:
    def test_normalizes_year_query_range(self):
        req = StoryDateRangeFilter(query_start=2025, query_end=2025)
        normalized_start, normalized_end, precision = req.normalize_query_range()

        assert normalized_start == date(2025, 1, 1)
        assert normalized_end == date(2025, 12, 31)
        assert precision == DatePrecision.YEAR

    def test_normalizes_date_query_range(self):
        req = StoryDateRangeFilter(query_start="2025-08-01", query_end="2025-08-31")
        normalized_start, normalized_end, precision = req.normalize_query_range()

        assert normalized_start == date(2025, 8, 1)
        assert normalized_end == date(2025, 8, 31)
        assert precision == DatePrecision.DATE


class TestStoryCreateRequestSchema:
    def test_valid_minimal_payload(self):
        req = StoryCreateRequest(
            title="A Story",
            content="Story content here",
            latitude=41.0,
            longitude=28.9,
        )
        assert req.title == "A Story"
        assert req.summary is None
        assert req.place_name is None

    def test_rejects_empty_title(self):
        with pytest.raises(ValidationError):
            StoryCreateRequest(title="", content="content", latitude=0, longitude=0)

    def test_rejects_title_too_long(self):
        with pytest.raises(ValidationError):
            StoryCreateRequest(title="x" * 256, content="content", latitude=0, longitude=0)

    def test_rejects_empty_content(self):
        with pytest.raises(ValidationError):
            StoryCreateRequest(title="Title", content="", latitude=0, longitude=0)

    def test_rejects_latitude_out_of_range(self):
        with pytest.raises(ValidationError):
            StoryCreateRequest(title="Title", content="content", latitude=91.0, longitude=0)

    def test_rejects_longitude_out_of_range(self):
        with pytest.raises(ValidationError):
            StoryCreateRequest(title="Title", content="content", latitude=0, longitude=181.0)

    def test_accepts_boundary_coordinates(self):
        req = StoryCreateRequest(title="Title", content="content", latitude=-90.0, longitude=-180.0)
        assert req.latitude == -90.0
        assert req.longitude == -180.0


class TestStoryUpdateRequestSchema:
    def test_valid_payload(self):
        req = StoryUpdateRequest(
            title="Updated",
            content="Updated content",
            latitude=39.9,
            longitude=32.8,
            place_name="Ankara",
        )
        assert req.title == "Updated"
        assert req.place_name == "Ankara"

    def test_rejects_empty_title(self):
        with pytest.raises(ValidationError):
            StoryUpdateRequest(title="", content="content", latitude=0, longitude=0)

    def test_rejects_latitude_out_of_range(self):
        with pytest.raises(ValidationError):
            StoryUpdateRequest(title="Title", content="content", latitude=-91.0, longitude=0)


class TestStoryBoundsFilterSchema:
    def test_valid_complete_bounds(self):
        bounds = StoryBoundsFilter(min_lat=40.0, max_lat=42.0, min_lng=28.0, max_lng=30.0)
        assert bounds.min_lat == 40.0
        assert bounds.max_lat == 42.0

    def test_accepts_all_none(self):
        bounds = StoryBoundsFilter()
        assert bounds.min_lat is None
        assert bounds.max_lat is None
        assert bounds.min_lng is None
        assert bounds.max_lng is None

    def test_rejects_partial_bounds(self):
        with pytest.raises(ValidationError, match="must be provided together"):
            StoryBoundsFilter(min_lat=40.0, max_lat=42.0)

    def test_rejects_min_lat_greater_than_max_lat(self):
        with pytest.raises(ValidationError, match="min_lat must be less than or equal to max_lat"):
            StoryBoundsFilter(min_lat=42.0, max_lat=40.0, min_lng=28.0, max_lng=30.0)

    def test_rejects_min_lng_greater_than_max_lng(self):
        with pytest.raises(ValidationError, match="min_lng must be less than or equal to max_lng"):
            StoryBoundsFilter(min_lat=40.0, max_lat=42.0, min_lng=30.0, max_lng=28.0)

    def test_rejects_out_of_range_latitude(self):
        with pytest.raises(ValidationError):
            StoryBoundsFilter(min_lat=-91.0, max_lat=42.0, min_lng=28.0, max_lng=30.0)

    def test_rejects_out_of_range_longitude(self):
        with pytest.raises(ValidationError):
            StoryBoundsFilter(min_lat=40.0, max_lat=42.0, min_lng=28.0, max_lng=181.0)


class TestMediaUploadRequestSchema:
    def test_valid_image_upload(self):
        req = MediaUploadRequest(media_type=MediaType.IMAGE)
        assert req.media_type == MediaType.IMAGE
        assert req.alt_text is None
        assert req.caption is None
        assert req.sort_order == 0

    def test_valid_with_all_fields(self):
        req = MediaUploadRequest(
            media_type=MediaType.AUDIO,
            alt_text="A sound clip",
            caption="Recording from 1920",
            transcript="Reviewed transcript",
            sort_order=3,
        )
        assert req.alt_text == "A sound clip"
        assert req.caption == "Recording from 1920"
        assert req.transcript == "Reviewed transcript"
        assert req.sort_order == 3

    def test_trims_transcript(self):
        req = MediaUploadRequest(media_type=MediaType.AUDIO, transcript="  Reviewed transcript  ")

        assert req.transcript == "Reviewed transcript"

    def test_normalizes_whitespace_only_transcript_to_none(self):
        req = MediaUploadRequest(media_type=MediaType.AUDIO, transcript="   ")

        assert req.transcript is None

    def test_rejects_negative_sort_order(self):
        with pytest.raises(ValidationError):
            MediaUploadRequest(media_type=MediaType.IMAGE, sort_order=-1)

    def test_rejects_alt_text_too_long(self):
        with pytest.raises(ValidationError):
            MediaUploadRequest(media_type=MediaType.IMAGE, alt_text="x" * 501)

    def test_rejects_caption_too_long(self):
        with pytest.raises(ValidationError):
            MediaUploadRequest(media_type=MediaType.IMAGE, caption="x" * 501)


class TestCommentCreateRequestSchema:
    def test_valid_payload(self):
        req = CommentCreateRequest(content="This is a valid comment")
        assert req.content == "This is a valid comment"

    def test_trims_surrounding_whitespace(self):
        req = CommentCreateRequest(content="  This is a valid comment  ")
        assert req.content == "This is a valid comment"

    def test_rejects_empty_content(self):
        with pytest.raises(ValidationError):
            CommentCreateRequest(content="")

    def test_rejects_whitespace_only_content(self):
        with pytest.raises(ValidationError):
            CommentCreateRequest(content="   ")

    def test_rejects_too_long_content(self):
        with pytest.raises(ValidationError):
            CommentCreateRequest(content="x" * 5001)


def _make_story_obj(**overrides):
    base = {
        "id": uuid.uuid4(),
        "title": "Test Story",
        "summary": "Summary",
        "content": "Content",
        "place_name": "Istanbul",
        "latitude": 41.0,
        "longitude": 28.9,
        "date_start": date(1453, 1, 1),
        "date_end": date(1453, 12, 31),
        "date_precision": DatePrecision.YEAR,
        "status": StoryStatus.PUBLISHED,
        "visibility": StoryVisibility.PUBLIC,
        "created_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestStoryResponseFromOrmWithAuthor:
    def test_maps_all_fields(self):
        story = _make_story_obj()
        resp = StoryResponse.from_orm_with_author(story, "authorname")

        assert resp.id == story.id
        assert resp.title == "Test Story"
        assert resp.author == "authorname"
        assert resp.place_name == "Istanbul"
        assert resp.latitude == 41.0
        assert resp.status == StoryStatus.PUBLISHED

    def test_year_precision_single_year_label(self):
        story = _make_story_obj(
            date_start=date(1453, 1, 1),
            date_end=date(1453, 12, 31),
            date_precision=DatePrecision.YEAR,
        )
        resp = StoryResponse.from_orm_with_author(story, "author")
        assert resp.date_label == "1453"

    def test_year_precision_range_label(self):
        story = _make_story_obj(
            date_start=date(1920, 1, 1),
            date_end=date(1923, 12, 31),
            date_precision=DatePrecision.YEAR,
        )
        resp = StoryResponse.from_orm_with_author(story, "author")
        assert resp.date_label == "1920 - 1923"

    def test_date_precision_single_date_label(self):
        story = _make_story_obj(
            date_start=date(1453, 5, 29),
            date_end=date(1453, 5, 29),
            date_precision=DatePrecision.DATE,
        )
        resp = StoryResponse.from_orm_with_author(story, "author")
        assert resp.date_label == "1453-05-29"

    def test_date_precision_range_label(self):
        story = _make_story_obj(
            date_start=date(1453, 5, 29),
            date_end=date(1453, 6, 15),
            date_precision=DatePrecision.DATE,
        )
        resp = StoryResponse.from_orm_with_author(story, "author")
        assert resp.date_label == "1453-05-29 - 1453-06-15"

    def test_no_dates_returns_none_label(self):
        story = _make_story_obj(
            date_start=None,
            date_end=None,
            date_precision=None,
        )
        resp = StoryResponse.from_orm_with_author(story, "author")
        assert resp.date_label is None

    def test_start_only_with_year_precision(self):
        story = _make_story_obj(
            date_start=date(1920, 1, 1),
            date_end=None,
            date_precision=DatePrecision.YEAR,
        )
        resp = StoryResponse.from_orm_with_author(story, "author")
        assert resp.date_label == "1920"

    def test_start_only_with_date_precision(self):
        story = _make_story_obj(
            date_start=date(1920, 3, 15),
            date_end=None,
            date_precision=DatePrecision.DATE,
        )
        resp = StoryResponse.from_orm_with_author(story, "author")
        assert resp.date_label == "1920-03-15"
