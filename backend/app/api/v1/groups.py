from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.core.deps import CurrentUserID, SessionDep, require_role
from app.models.enums import UserRole
from app.schemas.auth import UserResponse
from app.schemas.contest import ContestResponse
from app.schemas.group import GroupCreate, GroupResponse
from app.services import contest_service, group_service

router = APIRouter(prefix="/groups", tags=["groups"])

TeacherDep = Annotated[int, Depends(require_role(UserRole.teacher))]


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(body: GroupCreate, session: SessionDep, teacher_id: TeacherDep):
    group = await group_service.create_group(session, teacher_id, body.name, body.description)
    await session.commit()
    return group


@router.get("", response_model=list[GroupResponse])
async def list_groups(session: SessionDep, user_id: CurrentUserID):
    from sqlalchemy import select
    from app.models.user import User
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    return await group_service.list_groups(session, user_id, user.role)


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(group_id: int, session: SessionDep, _: CurrentUserID):
    return await group_service.get_group(session, group_id)


@router.get("/{group_id}/members", response_model=list[UserResponse])
async def get_members(group_id: int, session: SessionDep, _: CurrentUserID):
    return await group_service.get_members(session, group_id)


@router.post("/{group_id}/members", status_code=204)
async def add_member(
    group_id: int,
    session: SessionDep,
    teacher_id: TeacherDep,
    username: str = Body(..., embed=True),
):
    await group_service.add_member_by_username(session, group_id, teacher_id, username)
    await session.commit()


@router.get("/{group_id}/contests", response_model=list[ContestResponse])
async def list_group_contests(group_id: int, session: SessionDep, _: CurrentUserID):
    return await contest_service.list_contests_for_group(session, group_id)


@router.delete("/{group_id}/members/{user_id}", status_code=204)
async def remove_member(
    group_id: int, user_id: int, session: SessionDep, teacher_id: TeacherDep
):
    await group_service.remove_member(session, group_id, teacher_id, user_id)
    await session.commit()
