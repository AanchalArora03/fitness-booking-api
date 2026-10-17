from datetime import datetime, timezone

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    date_time: AwareDatetime = Field(alias="dateTime")
    instructor: str = Field(min_length=1, max_length=100)
    available_slots: int = Field(
        alias="availableSlots", strict=True, gt=0, le=2147483647
    )

    @field_validator("name", "instructor", mode="before")
    @classmethod
    def strip_text(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("date_time")
    @classmethod
    def require_future_date(cls, value):
        if value <= datetime.now(timezone.utc):
            raise ValueError("Class date must be in the future.")
        return value


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date_time: AwareDatetime = Field(serialization_alias="dateTime")
    instructor: str
    available_slots: int = Field(serialization_alias="availableSlots")
