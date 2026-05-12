import uuid

import pytest
from sqlalchemy import select

from app.db.enums import NotificationEventType
from app.db.notification import Notification
from app.db.story import Story
from app.db.user import User


@pytest.mark.asyncio
class TestStoryNotificationFlow:
    async def _register_and_login(self, client, username, email, password):
        await client.post(
            "/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        return login_resp.json()["access_token"]

    async def _create_story(self, client, token, title="Story for notifications"):
        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": title,
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "date_start": 1453,
                "date_end": 1453,
            },
        )
        assert create_resp.status_code == 201
        return create_resp.json()["id"]

    async def _get_notifications(self, db_session):
        result = await db_session.execute(
            select(Notification).order_by(Notification.created_at.asc(), Notification.id.asc())
        )
        return result.scalars().all()

    async def test_like_comment_and_save_create_notifications_for_story_author(self, client, db_session):
        author_token = await self._register_and_login(client, "notifauthor", "notifauthor@example.com", "NotifPass1!")
        actor_token = await self._register_and_login(client, "notifactor", "notifactor@example.com", "NotifPass2!")
        story_id = await self._create_story(client, author_token)

        like_resp = await client.post(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {actor_token}"},
        )
        comment_resp = await client.post(
            f"/stories/{story_id}/comments",
            headers={"Authorization": f"Bearer {actor_token}"},
            json={"content": "Great story"},
        )
        save_resp = await client.post(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {actor_token}"},
        )

        story = await db_session.get(Story, uuid.UUID(story_id))
        author = (await db_session.execute(select(User).where(User.username == "notifauthor"))).scalar_one()
        actor = (await db_session.execute(select(User).where(User.username == "notifactor"))).scalar_one()
        notifications = await self._get_notifications(db_session)

        assert like_resp.status_code == 200
        assert comment_resp.status_code == 201
        assert save_resp.status_code == 200
        assert len(notifications) == 3

        notifications_by_type = {notification.event_type: notification for notification in notifications}
        like_notification = notifications_by_type[NotificationEventType.STORY_LIKED]
        comment_notification = notifications_by_type[NotificationEventType.STORY_COMMENTED]
        save_notification = notifications_by_type[NotificationEventType.STORY_BOOKMARKED]

        assert like_notification.recipient_user_id == author.id
        assert like_notification.actor_user_id == actor.id
        assert like_notification.story_id == story.id
        assert like_notification.event_type == NotificationEventType.STORY_LIKED
        assert like_notification.comment_id is None

        assert comment_notification.recipient_user_id == author.id
        assert comment_notification.actor_user_id == actor.id
        assert comment_notification.story_id == story.id
        assert comment_notification.event_type == NotificationEventType.STORY_COMMENTED
        assert comment_notification.comment_id == uuid.UUID(comment_resp.json()["id"])

        assert save_notification.recipient_user_id == author.id
        assert save_notification.actor_user_id == actor.id
        assert save_notification.story_id == story.id
        assert save_notification.event_type == NotificationEventType.STORY_BOOKMARKED
        assert save_notification.comment_id is None

    async def test_self_interactions_do_not_create_notifications(self, client, db_session):
        author_token = await self._register_and_login(
            client, "notifselfauthor", "notifselfauthor@example.com", "NotifPass3!"
        )
        story_id = await self._create_story(client, author_token, title="Self notification story")

        like_resp = await client.post(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {author_token}"},
        )
        comment_resp = await client.post(
            f"/stories/{story_id}/comments",
            headers={"Authorization": f"Bearer {author_token}"},
            json={"content": "Talking to myself"},
        )
        save_resp = await client.post(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {author_token}"},
        )

        notifications = await self._get_notifications(db_session)

        assert like_resp.status_code == 200
        assert comment_resp.status_code == 201
        assert save_resp.status_code == 200
        assert notifications == []

    async def test_duplicate_requests_do_not_duplicate_active_interaction_notifications(self, client, db_session):
        author_token = await self._register_and_login(
            client, "notifdedupeauthor", "notifdedupeauthor@example.com", "NotifPass4!"
        )
        actor_token = await self._register_and_login(
            client, "notifdedupeactor", "notifdedupeactor@example.com", "NotifPass5!"
        )
        story_id = await self._create_story(client, author_token, title="Dedupe story")

        first_like = await client.post(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {actor_token}"},
        )
        second_like = await client.post(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {actor_token}"},
        )
        first_save = await client.post(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {actor_token}"},
        )
        second_save = await client.post(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {actor_token}"},
        )

        notifications = await self._get_notifications(db_session)
        event_types = [notification.event_type for notification in notifications]

        assert first_like.status_code == 200
        assert second_like.status_code == 200
        assert first_save.status_code == 200
        assert second_save.status_code == 200
        assert event_types.count(NotificationEventType.STORY_LIKED) == 1
        assert event_types.count(NotificationEventType.STORY_BOOKMARKED) == 1

    async def test_reliking_and_resaving_after_removal_create_fresh_notifications(self, client, db_session):
        author_token = await self._register_and_login(
            client, "notifrepeatauthor", "notifrepeatauthor@example.com", "NotifPass6!"
        )
        actor_token = await self._register_and_login(
            client, "notifrepeatactor", "notifrepeatactor@example.com", "NotifPass7!"
        )
        story_id = await self._create_story(client, author_token, title="Repeat story")

        await client.post(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {actor_token}"},
        )
        await client.delete(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {actor_token}"},
        )
        relike_resp = await client.post(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {actor_token}"},
        )

        await client.post(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {actor_token}"},
        )
        await client.delete(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {actor_token}"},
        )
        resave_resp = await client.post(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {actor_token}"},
        )

        notifications = await self._get_notifications(db_session)
        event_types = [notification.event_type for notification in notifications]

        assert relike_resp.status_code == 200
        assert resave_resp.status_code == 200
        assert event_types.count(NotificationEventType.STORY_LIKED) == 2
        assert event_types.count(NotificationEventType.STORY_BOOKMARKED) == 2

    async def test_deleting_comment_preserves_notification_history(self, client, db_session):
        author_token = await self._register_and_login(
            client, "notifdeleteauthor", "notifdeleteauthor@example.com", "NotifPass8!"
        )
        actor_token = await self._register_and_login(
            client, "notifdeleteactor", "notifdeleteactor@example.com", "NotifPass9!"
        )
        story_id = await self._create_story(client, author_token, title="Delete comment history story")

        comment_resp = await client.post(
            f"/stories/{story_id}/comments",
            headers={"Authorization": f"Bearer {actor_token}"},
            json={"content": "Temporary comment"},
        )
        assert comment_resp.status_code == 201

        delete_resp = await client.delete(
            f"/stories/{story_id}/comments/{comment_resp.json()['id']}",
            headers={"Authorization": f"Bearer {actor_token}"},
        )
        notifications = await self._get_notifications(db_session)

        assert delete_resp.status_code == 204
        assert len(notifications) == 1
        assert notifications[0].event_type == NotificationEventType.STORY_COMMENTED
        assert notifications[0].comment_id is None
