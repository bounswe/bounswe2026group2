from unittest.mock import MagicMock

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.badge import Badge
from app.db.base import Base
from app.db.enums import BadgeRuleType
from app.db.media_file import MediaFile  # noqa: F401
from app.db.notification import Notification  # noqa: F401
from app.db.session import get_db
from app.db.story import Story  # noqa: F401
from app.db.story_comment import StoryComment  # noqa: F401
from app.db.story_like import StoryLike  # noqa: F401
from app.db.story_report import StoryReport  # noqa: F401
from app.db.story_save import StorySave  # noqa: F401

# Import all models so Base.metadata knows about them
from app.db.user import User  # noqa: F401

BADGE_SEEDS = [
    {
        "name": "First Story",
        "description": "Published your very first story.",
        "icon_key": "badge_first_story",
        "rule_type": BadgeRuleType.FIRST_STORY,
    },
    {
        "name": "Story Teller",
        "description": "Published 5 stories on the platform.",
        "icon_key": "badge_story_milestone_5",
        "rule_type": BadgeRuleType.STORY_MILESTONE_5,
    },
    {
        "name": "Story Master",
        "description": "Published 10 stories on the platform.",
        "icon_key": "badge_story_milestone_10",
        "rule_type": BadgeRuleType.STORY_MILESTONE_10,
    },
]

# Build the async DB URL
# For tests, replace 'db' hostname with 'localhost' for local development
_url = settings.DATABASE_URL.replace("@db:", "@localhost:")
if _url.startswith("postgresql://"):
    _url = _url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql+asyncpg://", 1)


@pytest_asyncio.fixture
async def db_session():
    """Provide a per-test engine + session so everything shares one event loop."""
    engine = create_async_engine(_url, echo=False)

    # Reset the schema first so stale tables from earlier runs don't survive
    # and silently bypass new columns added to the ORM models.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    session = session_factory()
    session.add_all([Badge(**badge) for badge in BADGE_SEEDS])
    await session.commit()

    yield session

    # Teardown: close session, drop tables, dispose engine
    await session.close()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """Async HTTP client wired to the FastAPI app with test DB session."""
    from app.main import app

    # Override storage check so tests don't need MinIO
    from app.services import storage

    original_check = storage.check_connection
    storage.check_connection = MagicMock()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    storage.check_connection = original_check


@pytest_asyncio.fixture
async def seeded_db(db_session):
    """Insert a canonical set of sample data for tests that need a pre-populated DB.

    Creates 3 users and 5 stories (3 public/published, 1 draft, 1 private).
    All users share the password 'ValidPass1!' for login tests.

    Returns a dict:
        users   -> {key: User ORM object}
        stories -> {title: Story ORM object}
        public  -> list of published+public Story ORM objects
    """
    from datetime import date

    from app.db.enums import DatePrecision, StoryStatus, StoryVisibility, UserRole
    from tests.factories.story_factory import make_story_entity
    from tests.factories.user_factory import make_user_entity

    admin = make_user_entity(username="seed_admin", email="seed_admin@example.com", role=UserRole.ADMIN)
    alice = make_user_entity(username="seed_alice", email="seed_alice@example.com", display_name="Alice")
    bob = make_user_entity(username="seed_bob", email="seed_bob@example.com", display_name="Bob")
    db_session.add_all([admin, alice, bob])
    await db_session.flush()

    stories_data = [
        make_story_entity(
            user_id=alice.id,
            title="Fall of Constantinople",
            content="The Ottoman siege of 1453 ended the Byzantine Empire.",
            summary="Ottoman conquest of Constantinople in 1453.",
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            date_start=date(1453, 1, 1),
            date_end=date(1453, 12, 31),
            date_precision=DatePrecision.YEAR,
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
        ),
        make_story_entity(
            user_id=alice.id,
            title="Atatürk's Ankara",
            content="The founding of the Turkish Republic and its new capital.",
            summary="How Ankara became the capital of modern Turkey.",
            place_name="Ankara",
            latitude=39.9334,
            longitude=32.8597,
            date_start=date(1923, 1, 1),
            date_end=date(1938, 12, 31),
            date_precision=DatePrecision.YEAR,
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
        ),
        make_story_entity(
            user_id=bob.id,
            title="Ancient Ephesus",
            content="One of the greatest cities of the ancient world, located near modern Selçuk.",
            summary="The rise and fall of the ancient city of Ephesus.",
            place_name="Izmir",
            latitude=37.9395,
            longitude=27.3417,
            date_start=date(100, 1, 1),
            date_end=date(400, 12, 31),
            date_precision=DatePrecision.YEAR,
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
        ),
        make_story_entity(
            user_id=bob.id,
            title="Draft Story",
            content="A story not yet ready for publication.",
            summary="Unpublished draft.",
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            date_start=date(1900, 1, 1),
            date_end=date(1900, 12, 31),
            date_precision=DatePrecision.YEAR,
            status=StoryStatus.DRAFT,
            visibility=StoryVisibility.PUBLIC,
        ),
        make_story_entity(
            user_id=alice.id,
            title="Private Story",
            content="A story the author keeps private.",
            summary="Not visible to the public.",
            place_name="Bursa",
            latitude=40.1826,
            longitude=29.0665,
            date_start=date(1326, 1, 1),
            date_end=date(1326, 12, 31),
            date_precision=DatePrecision.YEAR,
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PRIVATE,
        ),
    ]

    db_session.add_all(stories_data)
    await db_session.commit()

    stories_by_title = {s.title: s for s in stories_data}
    public = [s for s in stories_data if s.status == StoryStatus.PUBLISHED and s.visibility == StoryVisibility.PUBLIC]

    return {
        "users": {"admin": admin, "alice": alice, "bob": bob},
        "stories": stories_by_title,
        "public": public,
    }
