
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DepotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    location_lat: float | None
    location_lng: float | None


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reg_no: str
    depot_id: int
    status: str


class VehicleCreate(BaseModel):
    reg_no: str = Field(min_length=1, max_length=20)
    depot_id: int = Field(gt=0)
    status: str = Field(min_length=1, max_length=30)

    @field_validator("reg_no", "status")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value


class DepotCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    location_lat: float = Field(ge=-90, le=90)
    location_lng: float = Field(ge=-180, le=180)
    depot_manager_id: int = Field(gt=0)

    @field_validator("code", "name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value
