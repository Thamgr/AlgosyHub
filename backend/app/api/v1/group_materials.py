from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, SessionDep, require_role
from app.models.enums import UserRole
from app.schemas.group_material import GroupMaterialCreate, GroupMaterialResponse
from app.services import group_material_service

router = APIRouter(prefix="/groups/{group_id}/materials", tags=["materials"])
TeacherDep = Annotated[int, Depends(require_role(UserRole.teacher))]


@router.get("", response_model=list[GroupMaterialResponse])
async def list_materials(group_id: int, session: SessionDep, user: CurrentUser):
    return await group_material_service.list_materials(session, group_id, user.id)


@router.post("", response_model=GroupMaterialResponse, status_code=201)
async def create_material(
    group_id: int, body: GroupMaterialCreate, session: SessionDep, teacher_id: TeacherDep
):
    material = await group_material_service.create_material(session, group_id, teacher_id, body)
    await session.commit()
    return material


@router.put("/{material_id}", response_model=GroupMaterialResponse)
async def update_material(
    group_id: int, material_id: int, body: GroupMaterialCreate,
    session: SessionDep, teacher_id: TeacherDep,
):
    material = await group_material_service.update_material(
        session, group_id, material_id, teacher_id, body,
    )
    await session.commit()
    return material
