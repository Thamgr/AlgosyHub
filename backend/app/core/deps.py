from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import decode_token
from app.models.enums import UserRole

bearer = HTTPBearer()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> int:
    user_id = decode_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user_id


CurrentUserID = Annotated[int, Depends(_get_current_user_id)]


def require_role(*roles: UserRole):
    async def checker(
        user_id: CurrentUserID,
        session: SessionDep,
    ) -> int:
        from sqlalchemy import select

        from app.models.user import User

        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user_id

    return checker
