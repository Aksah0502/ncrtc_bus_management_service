
from pydantic import BaseModel, ConfigDict


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
