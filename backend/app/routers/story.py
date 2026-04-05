from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.story import StoryListResponse
from app.services.story_service import list_available_stories

router = APIRouter(prefix="/stories", tags=["stories"])


@router.get("", response_model=StoryListResponse)
async def list_stories(db: AsyncSession = Depends(get_db)):
    return await list_available_stories(db)