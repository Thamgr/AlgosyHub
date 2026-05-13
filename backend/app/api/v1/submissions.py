from fastapi import APIRouter

from app.core.deps import CurrentUserID, SessionDep
from app.schemas.submission import SubmissionResponse, SubmitRequest
from app.services import submission_service

router = APIRouter(tags=["submissions"])


@router.post("/submissions", response_model=SubmissionResponse, status_code=201)
async def create_submission(
    body: SubmitRequest, session: SessionDep, user_id: CurrentUserID
):
    return await submission_service.submit(
        session,
        user_id,
        body.problem_id,
        body.contest_id,
        body.language,
        body.source_code,
    )


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: int, session: SessionDep, _: CurrentUserID
):
    return await submission_service.get_submission(session, submission_id)


@router.get(
    "/contests/{contest_id}/submissions", response_model=list[SubmissionResponse]
)
async def list_contest_submissions(
    contest_id: int,
    session: SessionDep,
    current_user_id: CurrentUserID,
    mine: bool = False,
    user_id: int | None = None,
):
    # mine=true → возвращаем только сабмиты текущего пользователя.
    target_user_id: int | None = None
    if mine:
        target_user_id = current_user_id
    elif user_id is not None:
        target_user_id = user_id
    return await submission_service.list_for_contest(
        session, contest_id, target_user_id
    )
