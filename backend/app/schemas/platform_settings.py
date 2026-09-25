from pydantic import BaseModel, ConfigDict, StrictBool


class PlatformSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    registration_enabled: bool = True
    ai_hints_enabled: bool = True


class PlatformSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    registration_enabled: StrictBool = True
    ai_hints_enabled: StrictBool = True
