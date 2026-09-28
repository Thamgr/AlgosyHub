from datetime import date as Date

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class MaterialLink(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str = Field(min_length=1, max_length=160)
    url: HttpUrl = Field(max_length=2048)

    @field_validator("url")
    @classmethod
    def no_credentials(cls, value: HttpUrl) -> HttpUrl:
        if value.username is not None or value.password is not None:
            raise ValueError("Links must not contain credentials")
        return value


class GroupMaterialCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=160)
    date: Date
    description: str = Field(default="", max_length=10000)
    links: list[MaterialLink] = Field(min_length=1, max_length=20)


class GroupMaterialResponse(GroupMaterialCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
