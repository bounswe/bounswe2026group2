from datetime import datetime, timezone

import pytest

from app.db.enums import StoryStatus, StoryVisibility
from app.db.story_comment import StoryComment
from app.db.story_like import StoryLike
from app.db.story_save import StorySave
from tests.factories.story_factory import make_story_entity
from tests.factories.user_factory import make_login_payload, make_user_entity


@pytest.mark.asyncio
class TestUserDashboardAPI:
    async def _create_user_and_token(self, client, db_session, *, username, email, password="ValidPass1!"):
        user = make_user_entity(username=username, email=email, password=password)
        db_session.add(user)
        await db_session.commit()

        login_resp = await client.post("/auth/login", json=make_login_payload(email=email, password=password))
        assert login_resp.status_code == 200
        return user, login_resp.json()["access_token"]

    @pytest.mark.parametrize(
        ("path", "method"),
        [
            ("/users/me/stories", "get"),
            ("/users/me/saved", "get"),
            ("/users/me/stats", "get"),
            ("/users/me/dashboard", "get"),
        ],
    )
    async def test_dashboard_endpoints_require_auth(self, client, path, method):
        resp = await getattr(client, method)(path)
        assert resp.status_code in (401, 403)

    async def test_list_my_stories_returns_paginated_non_deleted_user_stories(self, client, db_session):
        owner, token = await self._create_user_and_token(
            client,
            db_session,
            username="dashownerstories",
            email="dashownerstories@example.com",
        )
        other_user = make_user_entity(username="otherauthorstories", email="otherauthorstories@example.com")
        db_session.add(other_user)
        await db_session.flush()

        newest_story = make_story_entity(
            user_id=owner.id,
            title="Newest Story",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
        )
        newest_story.created_at = datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc)

        middle_story = make_story_entity(
            user_id=owner.id,
            title="Private Story",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PRIVATE,
        )
        middle_story.created_at = datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc)

        oldest_story = make_story_entity(
            user_id=owner.id,
            title="Draft Story",
            status=StoryStatus.DRAFT,
            visibility=StoryVisibility.PUBLIC,
        )
        oldest_story.created_at = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)

        deleted_story = make_story_entity(
            user_id=owner.id,
            title="Deleted Story",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
        )
        deleted_story.created_at = datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc)
        deleted_story.deleted_at = datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc)

        other_story = make_story_entity(
            user_id=other_user.id,
            title="Other User Story",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
        )

        db_session.add_all([newest_story, middle_story, oldest_story, deleted_story, other_story])
        await db_session.commit()

        resp = await client.get(
            "/users/me/stories?limit=2&offset=1",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["total"] == 3
        assert payload["limit"] == 2
        assert payload["offset"] == 1
        assert [story["title"] for story in payload["stories"]] == ["Private Story", "Draft Story"]
        assert payload["stories"][0]["visibility"] == "private"
        assert payload["stories"][1]["status"] == "draft"

    async def test_list_my_saved_returns_paginated_visible_saved_stories_only(self, client, db_session):
        saver, token = await self._create_user_and_token(
            client,
            db_session,
            username="dashsaver",
            email="dashsaver@example.com",
        )
        author = make_user_entity(username="savedauthor", email="savedauthor@example.com")
        db_session.add(author)
        await db_session.flush()

        visible_first = make_story_entity(user_id=author.id, title="Visible First")
        visible_second = make_story_entity(user_id=author.id, title="Visible Second")
        private_story = make_story_entity(
            user_id=author.id,
            title="Private Hidden",
            visibility=StoryVisibility.PRIVATE,
        )
        deleted_story = make_story_entity(user_id=author.id, title="Deleted Hidden")
        deleted_story.deleted_at = datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc)
        draft_story = make_story_entity(
            user_id=author.id,
            title="Draft Hidden",
            status=StoryStatus.DRAFT,
        )

        db_session.add_all([visible_first, visible_second, private_story, deleted_story, draft_story])
        await db_session.flush()

        db_session.add_all(
            [
                StorySave(
                    story_id=visible_first.id,
                    user_id=saver.id,
                    created_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
                ),
                StorySave(
                    story_id=visible_second.id,
                    user_id=saver.id,
                    created_at=datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc),
                ),
                StorySave(
                    story_id=private_story.id,
                    user_id=saver.id,
                    created_at=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
                ),
                StorySave(
                    story_id=deleted_story.id,
                    user_id=saver.id,
                    created_at=datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc),
                ),
                StorySave(
                    story_id=draft_story.id,
                    user_id=saver.id,
                    created_at=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
                ),
            ]
        )
        await db_session.commit()

        resp = await client.get(
            "/users/me/saved?limit=1&offset=1",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["total"] == 2
        assert payload["limit"] == 1
        assert payload["offset"] == 1
        assert [story["title"] for story in payload["stories"]] == ["Visible First"]

    async def test_get_my_stats_returns_story_and_engagement_totals(self, client, db_session):
        owner, token = await self._create_user_and_token(
            client,
            db_session,
            username="dashstatsowner",
            email="dashstatsowner@example.com",
        )
        liker_a = make_user_entity(username="likera", email="likera@example.com")
        liker_b = make_user_entity(username="likerb", email="likerb@example.com")
        liker_c = make_user_entity(username="likerc", email="likerc@example.com")
        db_session.add_all([liker_a, liker_b, liker_c])
        await db_session.flush()

        published_story = make_story_entity(user_id=owner.id, title="Published Story")
        private_story = make_story_entity(
            user_id=owner.id,
            title="Private Story",
            visibility=StoryVisibility.PRIVATE,
        )
        deleted_story = make_story_entity(user_id=owner.id, title="Deleted Story")
        deleted_story.deleted_at = datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc)
        db_session.add_all([published_story, private_story, deleted_story])
        await db_session.flush()

        db_session.add_all(
            [
                StoryLike(story_id=published_story.id, user_id=liker_a.id),
                StoryLike(story_id=published_story.id, user_id=liker_b.id),
                StoryLike(story_id=private_story.id, user_id=liker_c.id),
                StoryLike(story_id=deleted_story.id, user_id=liker_a.id),
                StoryComment(story_id=published_story.id, user_id=liker_a.id, content="One"),
                StoryComment(story_id=published_story.id, user_id=liker_b.id, content="Two"),
                StoryComment(story_id=private_story.id, user_id=liker_c.id, content="Three"),
                StoryComment(story_id=deleted_story.id, user_id=liker_a.id, content="Hidden"),
                StorySave(story_id=published_story.id, user_id=liker_a.id),
                StorySave(story_id=private_story.id, user_id=liker_b.id),
                StorySave(story_id=private_story.id, user_id=liker_c.id),
                StorySave(story_id=deleted_story.id, user_id=liker_a.id),
            ]
        )
        await db_session.commit()

        resp = await client.get("/users/me/stats", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        assert resp.json() == {
            "total_stories": 2,
            "total_likes_received": 3,
            "total_comments_received": 3,
            "total_saves_received": 3,
            "total_views_received": 0,
        }

    async def test_get_my_dashboard_combines_saved_count_and_top_stats(self, client, db_session):
        owner, token = await self._create_user_and_token(
            client,
            db_session,
            username="dashsummaryowner",
            email="dashsummaryowner@example.com",
        )
        other_author = make_user_entity(username="dashotherauthor", email="dashotherauthor@example.com")
        actor = make_user_entity(username="dashactor", email="dashactor@example.com")
        second_actor = make_user_entity(username="dashactor2", email="dashactor2@example.com")
        db_session.add_all([other_author, actor, second_actor])
        await db_session.flush()

        own_story = make_story_entity(user_id=owner.id, title="Own Story")
        second_own_story = make_story_entity(
            user_id=owner.id,
            title="Own Private Story",
            visibility=StoryVisibility.PRIVATE,
        )
        deleted_own_story = make_story_entity(user_id=owner.id, title="Removed Story")
        deleted_own_story.deleted_at = datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc)

        visible_saved_story = make_story_entity(user_id=other_author.id, title="Saved Visible Story")
        hidden_saved_story = make_story_entity(
            user_id=other_author.id,
            title="Saved Hidden Story",
            visibility=StoryVisibility.PRIVATE,
        )

        db_session.add_all([own_story, second_own_story, deleted_own_story, visible_saved_story, hidden_saved_story])
        await db_session.flush()

        db_session.add_all(
            [
                StoryLike(story_id=own_story.id, user_id=actor.id),
                StoryLike(story_id=second_own_story.id, user_id=second_actor.id),
                StoryComment(story_id=own_story.id, user_id=actor.id, content="Insightful"),
                StorySave(story_id=own_story.id, user_id=actor.id),
                StorySave(story_id=second_own_story.id, user_id=second_actor.id),
                StorySave(story_id=visible_saved_story.id, user_id=owner.id),
                StorySave(story_id=hidden_saved_story.id, user_id=owner.id),
            ]
        )
        await db_session.commit()

        resp = await client.get("/users/me/dashboard", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        assert resp.json() == {
            "stories_count": 2,
            "saved_count": 1,
            "total_likes_received": 2,
            "total_comments_received": 1,
            "total_saves_received": 2,
            "total_views_received": 0,
        }

    async def test_openapi_includes_dashboard_paths(self, client):
        resp = await client.get("/openapi.json")

        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/users/me/stories" in paths
        assert "/users/me/saved" in paths
        assert "/users/me/stats" in paths
        assert "/users/me/dashboard" in paths
        assert paths["/users/me/dashboard"]["get"]["summary"] == "Get current user dashboard summary"
