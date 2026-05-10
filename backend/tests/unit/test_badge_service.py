import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.enums import BadgeRuleType
from app.services.badge_service import check_and_award_story_badges, get_user_badges


def _make_badge(rule_type: BadgeRuleType, name: str = "Badge") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        description="A badge",
        icon_key=f"badge_{rule_type.value}",
        rule_type=rule_type,
    )


def _make_user_badge(user_id: uuid.UUID, badge: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        user_id=user_id,
        badge_id=badge.id,
        awarded_at=datetime.now(timezone.utc),
        badge=badge,
    )


@pytest.mark.asyncio
class TestCheckAndAwardStoryBadges:
    async def test_no_badges_awarded_when_story_count_is_zero(self):
        user_id = uuid.uuid4()
        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one=lambda: 0),  # story count
            SimpleNamespace(all=lambda: []),  # owned badge_ids
        ]

        await check_and_award_story_badges(db, user_id)

        db.add.assert_not_called()

    async def test_first_story_badge_awarded_on_first_story(self):
        user_id = uuid.uuid4()
        badge = _make_badge(BadgeRuleType.FIRST_STORY)

        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one=lambda: 1),   # story count = 1
            SimpleNamespace(all=lambda: []),          # no badges owned yet
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [badge])),  # batch badges
        ]
        db.add = MagicMock()

        await check_and_award_story_badges(db, user_id)

        assert db.add.call_count == 1
        awarded = db.add.call_args.args[0]
        assert awarded.user_id == user_id
        assert awarded.badge_id == badge.id

    async def test_milestone_5_badge_awarded_at_five_stories(self):
        user_id = uuid.uuid4()
        first_badge = _make_badge(BadgeRuleType.FIRST_STORY)
        milestone_badge = _make_badge(BadgeRuleType.STORY_MILESTONE_5)

        db = AsyncMock()
        # first_badge is already owned; batch returns both qualifying badges
        db.execute.side_effect = [
            SimpleNamespace(scalar_one=lambda: 5),
            SimpleNamespace(all=lambda: [(first_badge.id,)]),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [first_badge, milestone_badge])),
        ]
        db.add = MagicMock()

        await check_and_award_story_badges(db, user_id)

        assert db.add.call_count == 1
        awarded = db.add.call_args.args[0]
        assert awarded.badge_id == milestone_badge.id

    async def test_milestone_10_badge_awarded_at_ten_stories(self):
        user_id = uuid.uuid4()
        first_badge = _make_badge(BadgeRuleType.FIRST_STORY)
        milestone_5_badge = _make_badge(BadgeRuleType.STORY_MILESTONE_5)
        milestone_10_badge = _make_badge(BadgeRuleType.STORY_MILESTONE_10)

        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one=lambda: 10),
            SimpleNamespace(all=lambda: [(first_badge.id,), (milestone_5_badge.id,)]),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [first_badge, milestone_5_badge, milestone_10_badge])),
        ]
        db.add = MagicMock()

        await check_and_award_story_badges(db, user_id)

        assert db.add.call_count == 1
        awarded = db.add.call_args.args[0]
        assert awarded.badge_id == milestone_10_badge.id

    async def test_no_badge_awarded_when_already_owned(self):
        user_id = uuid.uuid4()
        badge = _make_badge(BadgeRuleType.FIRST_STORY)

        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one=lambda: 3),
            SimpleNamespace(all=lambda: [(badge.id,)]),  # already owns it
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [badge])),
        ]
        db.add = MagicMock()

        await check_and_award_story_badges(db, user_id)

        db.add.assert_not_called()

    async def test_no_badge_awarded_when_badge_row_missing_from_db(self):
        user_id = uuid.uuid4()

        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one=lambda: 1),
            SimpleNamespace(all=lambda: []),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])),  # badge not seeded
        ]
        db.add = MagicMock()

        await check_and_award_story_badges(db, user_id)

        db.add.assert_not_called()

    async def test_all_three_badges_awarded_at_ten_stories_when_none_owned(self):
        user_id = uuid.uuid4()
        b1 = _make_badge(BadgeRuleType.FIRST_STORY)
        b5 = _make_badge(BadgeRuleType.STORY_MILESTONE_5)
        b10 = _make_badge(BadgeRuleType.STORY_MILESTONE_10)

        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one=lambda: 10),
            SimpleNamespace(all=lambda: []),  # owns nothing
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [b1, b5, b10])),
        ]
        db.add = MagicMock()

        await check_and_award_story_badges(db, user_id)

        assert db.add.call_count == 3
        awarded_badge_ids = {c.args[0].badge_id for c in db.add.call_args_list}
        assert awarded_badge_ids == {b1.id, b5.id, b10.id}


@pytest.mark.asyncio
class TestGetUserBadges:
    async def test_returns_empty_list_when_no_badges(self):
        user_id = uuid.uuid4()
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        result = await get_user_badges(db, user_id)

        assert result == []

    async def test_returns_badge_responses_in_award_order(self):
        user_id = uuid.uuid4()
        badge1 = _make_badge(BadgeRuleType.FIRST_STORY, name="First Story")
        badge5 = _make_badge(BadgeRuleType.STORY_MILESTONE_5, name="Story Teller")
        ub1 = _make_user_badge(user_id, badge1)
        ub5 = _make_user_badge(user_id, badge5)

        db = AsyncMock()
        db.execute.return_value.all = lambda: [(ub1, badge1), (ub5, badge5)]

        result = await get_user_badges(db, user_id)

        assert len(result) == 2
        assert result[0].name == "First Story"
        assert result[0].rule_type == BadgeRuleType.FIRST_STORY
        assert result[1].name == "Story Teller"
        assert result[1].awarded_at == ub5.awarded_at
