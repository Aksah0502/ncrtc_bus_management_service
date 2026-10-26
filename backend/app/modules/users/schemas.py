from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ManagedRole = Literal["driver", "control_operator", "depot_manager"]


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    full_name: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1)
    role: ManagedRole
    depot_id: int | None = Field(default=None, gt=0)
    phone: str | None = Field(default=None, max_length=20)
    driving_license_number: str | None = Field(default=None, max_length=30)

    @field_validator("username", "full_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password cannot be blank.")
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes.")
        return value

    @field_validator("phone", "driving_license_number", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: str
    depot_id: int | None
    phone: str | None
    driving_license_number: str | None
