"""Seed one local test account via SQLAlchemy.

Usage (from repo root):
  docker compose run --rm -T backend sh -c 'cd /app && PYTHONPATH=/app python scripts/seed_test_account.py'
"""

from __future__ import annotations

import asyncio
import os
import uuid

from sqlalchemy import select

from app.db.enums import StoryStatus, StoryVisibility
from app.db.session import AsyncSessionLocal
from app.db.story import Story
from app.db.user import User
from app.services.auth_service import hash_password


async def main() -> None:
    email = os.environ.get("SEED_EMAIL", "test@gmail.com").strip().lower()
    password = os.environ.get("SEED_PASSWORD", "Test1234%")
    username = os.environ.get("SEED_USERNAME", "testuser")
    display_name = os.environ.get("SEED_DISPLAY_NAME", "Test User")
    story_id = uuid.UUID(os.environ.get("SEED_STORY_ID", "bb43034b-8e1a-49a8-92b9-56346f50767a"))
    story_title = os.environ.get("SEED_STORY_TITLE", "UAT seeded story")
    story_summary = os.environ.get("SEED_STORY_SUMMARY", "Playwright UAT fixture")
    story_content = os.environ.get("SEED_STORY_CONTENT", "Seeded body for anonymous view-count UAT.")

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            user = User(
                email=email,
                username=username,
                display_name=display_name,
                password_hash=hash_password(password),
                is_active=True,
            )
            db.add(user)
            user_action = "created"
        else:
            user.password_hash = hash_password(password)
            user.display_name = display_name
            user_action = "updated"

        await db.flush()

        story = (await db.execute(select(Story).where(Story.id == story_id))).scalar_one_or_none()
        if story is None:
            db.add(
                Story(
                    id=story_id,
                    user_id=user.id,
                    title=story_title,
                    summary=story_summary,
                    content=story_content,
                    status=StoryStatus.PUBLISHED,
                    visibility=StoryVisibility.PUBLIC,
                    view_count=0,
                    is_anonymous=False,
                )
            )
            story_action = "created"
        else:
            story.user_id = user.id
            story.title = story_title
            story.summary = story_summary
            story.content = story_content
            story.status = StoryStatus.PUBLISHED
            story.visibility = StoryVisibility.PUBLIC
            story.is_anonymous = False
            story.deleted_at = None
            story.deleted_by = None
            story.delete_reason = None
            story_action = "updated"

        await db.commit()

    print(f"{user_action} user: {email}")
    print(f"{story_action} story: {story_id} (owner={email})")


if __name__ == "__main__":
    asyncio.run(main())
