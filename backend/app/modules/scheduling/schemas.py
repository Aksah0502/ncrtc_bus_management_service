
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DutyCreate(BaseModel):
    service_date: date
    vehicle_id: int = Field(gt=0)
    driver_id: int = Field(gt=0)
    conductor_id: int | None = Field(default=None, gt=0)
    route_id: int = Field(gt=0)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time.")
        return self


class DutyPatch(BaseModel):
    service_date: date | None = None
    vehicle_id: int | None = Field(default=None, gt=0)
    driver_id: int | None = Field(default=None, gt=0)
    conductor_id: int | None = Field(default=None, gt=0)
    route_id: int | None = Field(default=None, gt=0)
    start_time: time | None = None
    end_time: time | None = None

    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time is not None and self.end_time is not None:
            if self.end_time <= self.start_time:
                raise ValueError("end_time must be later than start_time.")
        return self


class DutyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_date: date
    vehicle_id: int
    driver_id: int
    conductor_id: int | None
    route_id: int
    start_time: time
    end_time: time
    status: str
    ack_at: datetime | None
