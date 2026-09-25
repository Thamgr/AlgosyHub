from fastapi import APIRouter, HTTPException, Response

from app.core.deps import CurrentUser, SessionDep
from app.schemas.platform_settings import PlatformSettingsResponse, PlatformSettingsUpdate
from app.services import platform_settings_service

router = APIRouter(prefix="/platform-settings", tags=["platform-settings"])


@router.get("", response_model=PlatformSettingsResponse)
async def get_settings(session: SessionDep, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return await platform_settings_service.get_settings(session)


@router.patch("", response_model=PlatformSettingsResponse)
async def update_settings(
    body: PlatformSettingsUpdate, session: SessionDep, user: CurrentUser,
):
    if not user.is_platform_admin:
        raise HTTPException(403, "Требуются права администратора платформы")
    return await platform_settings_service.update_settings(session, body)
