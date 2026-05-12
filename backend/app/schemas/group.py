from pydantic import BaseModel

from app.schemas.auth import UserResponse


class GroupCreate(BaseModel):
    name: str
    description: str | None = None


class GroupResponse(BaseModel):
    id: int
    teacher_id: int
    name: str
    description: str | None

    model_config = {"from_attributes": True}
