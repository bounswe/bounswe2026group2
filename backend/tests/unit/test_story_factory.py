import uuid
from datetime import date

from app.db.enums import DatePrecision, StoryStatus, StoryVisibility
from app.db.story import Story
from tests.factories.story_factory import (
    DEFAULT_DATE_END,
    DEFAULT_DATE_START,
    DEFAULT_ENTITY_DATE_END,
    DEFAULT_ENTITY_DATE_START,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    DEFAULT_PLACE_NAME,
    DEFAULT_TITLE,
    make_story_entity,
    make_story_payload,
    make_story_update_payload,
)


class TestMakeStoryPayload:
    def test_defaults_produce_valid_create_request_fields(self):
        payload = make_story_payload()
        assert payload["title"] == DEFAULT_TITLE
        assert payload["place_name"] == DEFAULT_PLACE_NAME
        assert payload["latitude"] == DEFAULT_LATITUDE
        assert payload["longitude"] == DEFAULT_LONGITUDE
        assert payload["date_start"] == DEFAULT_DATE_START
        assert payload["date_end"] == DEFAULT_DATE_END
        assert "content" in payload

    def test_coordinates_are_within_valid_bounds(self):
        payload = make_story_payload()
        assert -90.0 <= payload["latitude"] <= 90.0
        assert -180.0 <= payload["longitude"] <= 180.0

    def test_date_range_is_valid(self):
        payload = make_story_payload()
        assert payload["date_start"] <= payload["date_end"]

    def test_suffix_makes_title_and_place_name_unique(self):
        p1 = make_story_payload(suffix=1)
        p2 = make_story_payload(suffix=2)
        assert p1["title"] != p2["title"]
        assert p1["place_name"] != p2["place_name"]

    def test_field_overrides_are_applied(self):
        payload = make_story_payload(
            title="Custom Title",
            place_name="Beyoğlu, Istanbul",
            latitude=41.0335,
            longitude=28.9775,
            date_start=1950,
            date_end=1960,
        )
        assert payload["title"] == "Custom Title"
        assert payload["place_name"] == "Beyoğlu, Istanbul"
        assert payload["latitude"] == 41.0335
        assert payload["longitude"] == 28.9775
        assert payload["date_start"] == 1950
        assert payload["date_end"] == 1960

    def test_optional_summary_omitted_when_none(self):
        payload = make_story_payload(summary=None)
        assert "summary" not in payload

    def test_optional_dates_omitted_when_none(self):
        payload = make_story_payload(date_start=None, date_end=None)
        assert "date_start" not in payload
        assert "date_end" not in payload


class TestMakeStoryUpdatePayload:
    def test_defaults_produce_valid_update_fields(self):
        payload = make_story_update_payload()
        assert "title" in payload
        assert "content" in payload
        assert "place_name" in payload
        assert "latitude" in payload
        assert "longitude" in payload

    def test_field_overrides_are_applied(self):
        payload = make_story_update_payload(
            title="Updated Title",
            place_name="Karaköy, Istanbul",
        )
        assert payload["title"] == "Updated Title"
        assert payload["place_name"] == "Karaköy, Istanbul"


class TestMakeStoryEntity:
    def test_returns_story_instance(self):
        story = make_story_entity(user_id=uuid.uuid4())
        assert isinstance(story, Story)

    def test_defaults_match_factory_constants(self):
        user_id = uuid.uuid4()
        story = make_story_entity(user_id=user_id)
        assert story.user_id == user_id
        assert story.title == DEFAULT_TITLE
        assert story.place_name == DEFAULT_PLACE_NAME
        assert story.latitude == DEFAULT_LATITUDE
        assert story.longitude == DEFAULT_LONGITUDE
        assert story.date_start == DEFAULT_ENTITY_DATE_START
        assert story.date_end == DEFAULT_ENTITY_DATE_END

    def test_default_dates_are_date_objects(self):
        story = make_story_entity(user_id=uuid.uuid4())
        assert isinstance(story.date_start, date)
        assert isinstance(story.date_end, date)

    def test_default_date_precision_is_year(self):
        story = make_story_entity(user_id=uuid.uuid4())
        assert story.date_precision == DatePrecision.YEAR

    def test_default_status_is_published_and_public(self):
        story = make_story_entity(user_id=uuid.uuid4())
        assert story.status == StoryStatus.PUBLISHED
        assert story.visibility == StoryVisibility.PUBLIC

    def test_suffix_makes_title_and_place_name_unique(self):
        uid = uuid.uuid4()
        s1 = make_story_entity(user_id=uid, suffix=1)
        s2 = make_story_entity(user_id=uid, suffix=2)
        assert s1.title != s2.title
        assert s1.place_name != s2.place_name

    def test_field_overrides_are_applied(self):
        user_id = uuid.uuid4()
        story = make_story_entity(
            user_id=user_id,
            title="Override Title",
            status=StoryStatus.DRAFT,
            visibility=StoryVisibility.PRIVATE,
            date_start=date(1970, 1, 1),
            date_end=date(1975, 12, 31),
            date_precision=DatePrecision.YEAR,
        )
        assert story.title == "Override Title"
        assert story.status == StoryStatus.DRAFT
        assert story.visibility == StoryVisibility.PRIVATE
        assert story.date_start == date(1970, 1, 1)
        assert story.date_end == date(1975, 12, 31)
        assert story.date_precision == DatePrecision.YEAR

    def test_exact_date_precision_accepted(self):
        story = make_story_entity(
            user_id=uuid.uuid4(),
            date_start=date(1965, 6, 12),
            date_end=date(1965, 6, 12),
            date_precision=DatePrecision.DATE,
        )
        assert story.date_start == date(1965, 6, 12)
        assert story.date_precision == DatePrecision.DATE

    def test_optional_fields_can_be_none(self):
        story = make_story_entity(
            user_id=uuid.uuid4(),
            summary=None,
            place_name=None,
            latitude=None,
            longitude=None,
            date_start=None,
            date_end=None,
            date_precision=None,
        )
        assert story.summary is None
        assert story.place_name is None
        assert story.latitude is None
        assert story.longitude is None
        assert story.date_start is None
        assert story.date_end is None
        assert story.date_precision is None
