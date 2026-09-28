from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.group_material import GroupMaterial
from app.repositories.group_repo import GroupRepository
from app.schemas.group_material import GroupMaterialCreate
from app.services.group_service import get_group, get_owned_group


async def list_materials(session: AsyncSession, group_id: int, user_id: int) -> list[GroupMaterial]:
    await get_group(session, group_id)
    if not await GroupRepository(session).can_read(group_id, user_id):
        raise AppError("Forbidden", 403)
    result = await session.execute(
        select(GroupMaterial)
        .where(GroupMaterial.group_id == group_id)
        .order_by(GroupMaterial.date.desc(), GroupMaterial.id.desc())
    )
    return list(result.scalars())


async def create_material(
    session: AsyncSession, group_id: int, teacher_id: int, body: GroupMaterialCreate
) -> GroupMaterial:
    await get_owned_group(session, group_id, teacher_id)
    material = GroupMaterial(
        group_id=group_id,
        title=body.title,
        date=body.date,
        description=body.description,
        links=[link.model_dump(mode="json") for link in body.links],
    )
    session.add(material)
    await session.flush()
    await session.refresh(material)
    return material


async def update_material(
    session: AsyncSession, group_id: int, material_id: int, teacher_id: int,
    body: GroupMaterialCreate,
) -> GroupMaterial:
    await get_owned_group(session, group_id, teacher_id)
    material = await session.scalar(
        select(GroupMaterial).where(
            GroupMaterial.id == material_id, GroupMaterial.group_id == group_id,
        )
    )
    if material is None:
        raise AppError("Material not found", 404)
    material.title = body.title
    material.date = body.date
    material.description = body.description
    material.links = [link.model_dump(mode="json") for link in body.links]
    await session.flush()
    await session.refresh(material)
    return material
