from fastapi import APIRouter, HTTPException

from app.core.deps import CurrentUserID, SessionDep
from app.models.enums import ExternalSource
from app.schemas.judge_account import JudgeAccountResponse, JudgeAccountUpsert
from app.services import judge_account_service

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/judge-accounts", response_model=list[JudgeAccountResponse])
async def list_judge_accounts(session: SessionDep, user_id: CurrentUserID):
    return await judge_account_service.list_for_user(session, user_id)


@router.put("/judge-accounts/{source}", response_model=JudgeAccountResponse)
async def upsert_judge_account(
    source: ExternalSource,
    body: JudgeAccountUpsert,
    session: SessionDep,
    user_id: CurrentUserID,
):
    account = await judge_account_service.upsert(
        session, user_id, source, body.handle.strip()
    )
    await session.commit()
    return account


@router.delete("/judge-accounts/{source}", status_code=204)
async def delete_judge_account(
    source: ExternalSource, session: SessionDep, user_id: CurrentUserID
):
    deleted = await judge_account_service.delete(session, user_id, source)
    if not deleted:
        raise HTTPException(status_code=404, detail="Account not connected")
    await session.commit()
