from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.story import StoryListResponse
from app.services.story_service import (
    list_available_stories,
    search_available_stories_by_place,
)

router = APIRouter(prefix="/stories", tags=["stories"])


@router.get("", response_model=StoryListResponse)
async def list_stories(db: AsyncSession = Depends(get_db)):
    return await list_available_stories(db)


@router.get("/search", response_model=StoryListResponse)
async def search_stories(
    place_name: str = Query(min_length=1, max_length=255),
    db: AsyncSession = Depends(get_db),
):
    return await search_available_stories_by_place(db, place_name)