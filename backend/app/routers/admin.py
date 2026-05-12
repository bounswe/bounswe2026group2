from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.db.user import User
from app.services.admin_service import ensure_admin_user

router = APIRouter(prefix="/stories/admin", tags=["admin"])


async def get_admin_context(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, AsyncSession]:
    ensure_admin_user(current_user)
    return current_user, db
