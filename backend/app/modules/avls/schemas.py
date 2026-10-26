from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class GPSPingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ts: datetime
    lat: float
    lng: float
    speed_kmh: float | None
    ignition_on: bool | None


class LiveLocationResponse(BaseModel):
    vehicle_id: int
    reg_no: str
    depot_id: int
    lat: float
    lng: float
    speed_kmh: float | None
    ts: datetime


class LiveDetailsResponse(BaseModel):
    vehicle_id: int
    reg_no: str
    driver_name: str | None
    driver_phone: str | None
    driver_driving_license_number: str | None
    route_code: str | None
    route_name: str | None
    pings: list[GPSPingResponse]


class LocationHistoryResponse(BaseModel):
    vehicle_id: int
    date: date
    pings: list[GPSPingResponse]
