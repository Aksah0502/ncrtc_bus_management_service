
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.authorization import resolve_depot_filter
from app.db.session import get_db
from app.modules.fleet.models import Depot, Vehicle
from app.modules.fleet.schemas import DepotResponse, VehicleResponse
from app.modules.users.models import User
from fastapi import HTTPException, status
from app.core.authorization import ensure_depot_access

router = APIRouter(prefix="/fleet", tags=["Fleet"])


@router.get("/depots", response_model=list[DepotResponse])
def list_depots(
    depot_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed_depot_id = resolve_depot_filter(current_user, depot_id)
    statement = select(Depot).order_by(Depot.id)

    if allowed_depot_id is not None:
        statement = statement.where(Depot.id == allowed_depot_id)

    return db.scalars(statement).all()


@router.get("/vehicles", response_model=list[VehicleResponse])
def list_vehicles(
    depot_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed_depot_id = resolve_depot_filter(current_user, depot_id)
    statement = select(Vehicle).order_by(Vehicle.id)

    if allowed_depot_id is not None:
        statement = statement.where(Vehicle.depot_id == allowed_depot_id)

    return db.scalars(statement).all()


@router.get(
    "/vehicles/{vehicle_id}",
    response_model=VehicleResponse,
)
def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vehicle = db.get(Vehicle, vehicle_id)

    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        )

    ensure_depot_access(current_user, vehicle.depot_id)
    return vehicle

