from fastapi import APIRouter, HTTPException

from app.core.avatars import AVATAR_OPTIONS
from app.core.deps import CurrentUser, CurrentUserID, SessionDep
from app.models.enums import ExternalSource
from app.schemas.auth import AvatarOption, UpdateProfileRequest, UserResponse
from app.schemas.judge_account import JudgeAccountResponse, JudgeAccountUpsert
from app.services import judge_account_service, platform_settings_service, user_service

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/avatar-options", response_model=list[AvatarOption])
async def avatar_options(_: CurrentUserID):
    return [{"emoji": emoji, "label": label} for emoji, label in AVATAR_OPTIONS]


@router.patch("", response_model=UserResponse)
async def update_me(
    body: UpdateProfileRequest, session: SessionDep, user: CurrentUser
):
    if "full_name" in body.model_fields_set:
        await platform_settings_service.require_identity_editing(session, user)
    updated = await user_service.update_profile(
        session, user.id, **body.model_dump(exclude_unset=True)
    )
    await session.commit()
    return updated


@router.get("/judge-accounts", response_model=list[JudgeAccountResponse])
async def list_judge_accounts(session: SessionDep, user_id: CurrentUserID):
    return await judge_account_service.list_for_user(session, user_id)


@router.put("/judge-accounts/{source}", response_model=JudgeAccountResponse)
async def upsert_judge_account(
    source: ExternalSource,
    body: JudgeAccountUpsert,
    session: SessionDep,
    user: CurrentUser,
):
    await platform_settings_service.require_identity_editing(session, user)
    account = await judge_account_service.upsert(
        session, user.id, source, body.handle.strip()
    )
    await session.commit()
    return account


@router.delete("/judge-accounts/{source}", status_code=204)
async def delete_judge_account(
    source: ExternalSource, session: SessionDep, user: CurrentUser
):
    await platform_settings_service.require_identity_editing(session, user)
    deleted = await judge_account_service.delete(session, user.id, source)
    if not deleted:
        raise HTTPException(status_code=404, detail="Account not connected")
    await session.commit()
