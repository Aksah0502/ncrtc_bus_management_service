
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    lat: float
    lng: float


class RouteStopInput(BaseModel):
    sequence: int = Field(ge=1)
    stop_id: int = Field(gt=0)
    planned_offset_min: int = Field(ge=0)


class RouteCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    depot_id: int = Field(gt=0)
    route_stops: list[RouteStopInput] = Field(min_length=1)

    @field_validator("route_stops")
    @classmethod
    def validate_sequences(cls, stops):
        sequences = [stop.sequence for stop in stops]
        if len(sequences) != len(set(sequences)):
            raise ValueError("Stop sequence numbers must be unique.")
        return stops


class RoutePatch(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    route_stops: list[RouteStopInput] | None = None

    @field_validator("route_stops")
    @classmethod
    def validate_sequences(cls, stops):
        if stops is not None:
            sequences = [stop.sequence for stop in stops]
            if len(sequences) != len(set(sequences)):
                raise ValueError("Stop sequence numbers must be unique.")
        return stops


class RouteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    depot_id: int


class RouteStopResponse(BaseModel):
    sequence: int
    stop_id: int
    planned_offset_min: int
    stop: StopResponse


class RouteDetailResponse(RouteResponse):
    route_stops: list[RouteStopResponse]
