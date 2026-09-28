from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.avatars import AVATAR_EMOJIS
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
    avatar_emoji: str = ""
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
    avatar_emoji: str = ""
    role: UserRole
    stats: UserStats


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(default="", max_length=201)
    avatar_emoji: str = Field(default="", max_length=32)

    @field_validator("avatar_emoji")
    @classmethod
    def validate_avatar(cls, value: str) -> str:
        if value and value not in AVATAR_EMOJIS:
            raise ValueError("Выберите эмодзи из списка")
        return value


class AvatarOption(BaseModel):
    emoji: str
    label: str
