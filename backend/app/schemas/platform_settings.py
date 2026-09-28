from pydantic import BaseModel, ConfigDict, StrictBool


class PlatformSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    registration_enabled: bool = True
    ai_hints_enabled: bool = True
    show_problem_tags: bool = False
    show_problem_difficulty: bool = False
    student_identity_locked: bool = False


class PlatformSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    registration_enabled: StrictBool = True
    ai_hints_enabled: StrictBool = True
    show_problem_tags: StrictBool = False
    show_problem_difficulty: StrictBool = False
    student_identity_locked: StrictBool = False
