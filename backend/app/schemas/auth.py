from pydantic import BaseModel, ConfigDict, Field

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
    full_name: str = ""
    role: UserRole
    is_platform_admin: bool = False

    model_config = {"from_attributes": True}


class UserStats(BaseModel):
    solved_problems: int
    total_submissions: int
    accepted_submissions: int
    success_rate: float  # 0..1, доля accepted среди всех посылок


class UserProfileResponse(BaseModel):
    id: int
    username: str
    full_name: str = ""
    role: UserRole
    stats: UserStats


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(default="", max_length=201)
