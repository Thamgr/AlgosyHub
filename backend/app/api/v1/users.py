from fastapi import APIRouter

from app.core.deps import SessionDep
from app.schemas.auth import UserProfileResponse, UserStats
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{username}", response_model=UserProfileResponse)
async def get_user_profile(username: str, session: SessionDep):
    """Публичный профиль пользователя.

    Аутентификация не требуется: страница профиля общедоступна, как и
    стандартный профиль на любом judge'е.
    """
    user = await user_service.get_by_username(session, username)
    stats = await user_service.get_stats(session, user.id)
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        stats=UserStats(**stats),
    )
