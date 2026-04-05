import pytest
from pydantic import ValidationError

from app.models.story import StoryCreateRequest, StoryUpdateRequest
from app.models.user import UserRegisterRequest, UserLoginRequest


class TestUserRegisterRequestSchema:
    def test_valid_payload(self):
        req = UserRegisterRequest(
            username="john", email="john@example.com", password="MyPass1!"
        )
        assert req.username == "john"
        assert req.email == "john@example.com"

    def test_username_too_short(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                username="ab", email="a@b.com", password="MyPass1!"
            )

    def test_username_too_long(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                username="a" * 51, email="a@b.com", password="MyPass1!"
            )

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                username="john", email="not-an-email", password="MyPass1!"
            )

    def test_display_name_optional(self):
        req = UserRegisterRequest(
            username="john", email="john@example.com", password="MyPass1!"
        )
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

    def test_create_accepts_single_date_start_only(self):
        payload = self._base_story_payload() | {"date_start": 1453, "date_end": None}
        req = StoryCreateRequest(**payload)

        assert req.date_start == 1453
        assert req.date_end is None

    def test_create_rejects_invalid_date_range(self):
        payload = self._base_story_payload() | {"date_start": 1453, "date_end": 1400}

        with pytest.raises(ValidationError, match="date_end must be greater than or equal to date_start"):
            StoryCreateRequest(**payload)

    @pytest.mark.parametrize("field_name, field_value", [("date_start", 0), ("date_end", 10000)])
    def test_create_rejects_out_of_bounds_dates(self, field_name: str, field_value: int):
        payload = self._base_story_payload() | {field_name: field_value}

        with pytest.raises(ValidationError):
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
