from fastapi import APIRouter

from app.core.deps import CurrentUserID, SessionDep
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest, session: SessionDep):
    user = await auth_service.register(
        session, body.username, body.password, body.role
    )
    await session.commit()
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: SessionDep):
    token = await auth_service.login(session, body.username, body.password)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(user_id: CurrentUserID, session: SessionDep):
    return await auth_service.get_user(session, user_id)
