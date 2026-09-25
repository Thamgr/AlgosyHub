from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.platform_settings import PlatformSettings
from app.schemas.platform_settings import PlatformSettingsResponse, PlatformSettingsUpdate


async def get_settings(session: AsyncSession) -> PlatformSettingsResponse:
    settings = await session.get(PlatformSettings, 1, populate_existing=True)
    if settings is None:
        return PlatformSettingsResponse()
    return PlatformSettingsResponse.model_validate(settings)


async def update_settings(
    session: AsyncSession, body: PlatformSettingsUpdate
) -> PlatformSettingsResponse:
    changes = body.model_dump(exclude_unset=True)
    if changes:
        # Atomic partial upsert: independent switches cannot overwrite each other.
        insert = sqlite_insert if session.get_bind().dialect.name == "sqlite" else pg_insert
        statement = insert(PlatformSettings).values(id=1, **changes)
        await session.execute(statement.on_conflict_do_update(index_elements=["id"], set_=changes))
        await session.commit()
    return await get_settings(session)


async def require_registration(session: AsyncSession) -> None:
    if not (await get_settings(session)).registration_enabled:
        raise AppError("Регистрация отключена администратором", 403)


async def require_ai_hints(session: AsyncSession) -> None:
    if not (await get_settings(session)).ai_hints_enabled:
        raise AppError("AI-подсказки отключены администратором", 403)
