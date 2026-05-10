import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.badge import Badge, UserBadge
from app.db.enums import BadgeRuleType
from app.db.story import Story
from app.models.user import BadgeResponse

# Maps each rule type to the minimum published-story count required.
_STORY_COUNT_RULES: dict[BadgeRuleType, int] = {
    BadgeRuleType.FIRST_STORY: 1,
    BadgeRuleType.STORY_MILESTONE_5: 5,
    BadgeRuleType.STORY_MILESTONE_10: 10,
}


async def check_and_award_story_badges(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Award any story-count-based badges the user has newly earned."""
    count_result = await db.execute(
        select(func.count(Story.id)).where(
            Story.user_id == user_id,
            Story.deleted_at.is_(None),
        )
    )
    story_count = count_result.scalar_one()

    qualifying_rule_types = [rt for rt, threshold in _STORY_COUNT_RULES.items() if story_count >= threshold]
    if not qualifying_rule_types:
        return

    owned_result = await db.execute(select(UserBadge.badge_id).where(UserBadge.user_id == user_id))
    owned_badge_ids = {row[0] for row in owned_result.all()}

    badges_result = await db.execute(select(Badge).where(Badge.rule_type.in_(qualifying_rule_types)))
    badges = badges_result.scalars().all()

    for badge in badges:
        if badge.id not in owned_badge_ids:
            db.add(UserBadge(user_id=user_id, badge_id=badge.id, awarded_at=datetime.now(timezone.utc)))


async def get_user_badges(db: AsyncSession, user_id: uuid.UUID) -> list[BadgeResponse]:
    """Return all badges awarded to a user, ordered by award date."""
    result = await db.execute(
        select(UserBadge, Badge)
        .join(Badge, UserBadge.badge_id == Badge.id)
        .where(UserBadge.user_id == user_id)
        .order_by(UserBadge.awarded_at)
    )
    return [
        BadgeResponse(
            id=badge.id,
            name=badge.name,
            description=badge.description,
            icon_key=badge.icon_key,
            rule_type=badge.rule_type,
            awarded_at=user_badge.awarded_at,
        )
        for user_badge, badge in result.all()
    ]
