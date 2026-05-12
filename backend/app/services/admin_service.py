from fastapi import HTTPException, status

from app.db.enums import UserRole
from app.db.user import User


def ensure_admin_user(current_user: User) -> None:
    """Require the current user to have admin privileges."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
