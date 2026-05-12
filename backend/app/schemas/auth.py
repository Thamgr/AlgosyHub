from pydantic import BaseModel, EmailStr

from app.models.enums import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: UserRole

    model_config = {"from_attributes": True}
