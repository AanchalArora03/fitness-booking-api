from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from schemas.fitness_class import ClassResponse


class BookingCreate(BaseModel):
    class_id: int = Field(strict=True, gt=0, le=9223372036854775807)
    client_name: str = Field(min_length=1, max_length=100)
    client_email: EmailStr = Field(max_length=255)

    @field_validator("client_name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: int
    client_name: str
    client_email: EmailStr
    fitness_class: ClassResponse
