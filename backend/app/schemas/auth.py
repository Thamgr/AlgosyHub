from pydantic import BaseModel

from app.models.enums import UserRole


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole

    model_config = {"from_attributes": True}
