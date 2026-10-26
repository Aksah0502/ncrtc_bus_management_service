
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.authorization import ensure_depot_access, resolve_depot_filter
from app.db.session import get_db
from app.modules.avls.models import GPSPing
from app.modules.fleet.models import Depot, Vehicle
from app.modules.fleet.schemas import (
    DepotCreate,
    DepotResponse,
    VehicleCreate,
    VehicleResponse,
)
from app.modules.incidents.models import Incident
from app.modules.routes.models import Route
from app.modules.scheduling.models import Duty
from app.modules.users.models import User

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


@router.post(
    "/vehicles",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vehicle(
    payload: VehicleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    if db.get(Depot, payload.depot_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Depot not found.",
        )

    if db.scalar(select(Vehicle.id).where(Vehicle.reg_no == payload.reg_no)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle registration number is already in use.",
        )

    vehicle = Vehicle(
        reg_no=payload.reg_no,
        depot_id=payload.depot_id,
        status=payload.status,
    )
    db.add(vehicle)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle registration number or another database constraint conflicts with this vehicle.",
        ) from None

    db.refresh(vehicle)
    return vehicle


@router.delete(
    "/vehicles/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        )

    references = (
        ("published or historical duties", select(Duty.id).where(Duty.vehicle_id == vehicle.id)),
        ("GPS history", select(GPSPing.id).where(GPSPing.vehicle_id == vehicle.id)),
        ("incidents", select(Incident.id).where(Incident.vehicle_id == vehicle.id)),
    )
    for label, statement in references:
        if db.scalar(statement.limit(1)) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Vehicle cannot be deleted while it has {label}.",
            )

    db.delete(vehicle)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle is referenced by another operational record and cannot be deleted.",
        ) from None


@router.post(
    "/depots",
    response_model=DepotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_depot(
    payload: DepotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    if db.scalar(select(Depot.id).where(Depot.code == payload.code)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Depot code is already in use.",
        )

    manager = db.get(User, payload.depot_manager_id)
    if manager is None or manager.role != "depot_manager":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The selected user is not a depot manager.",
        )
    if manager.depot_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The selected depot manager is already assigned to a depot.",
        )

    depot = Depot(
        code=payload.code,
        name=payload.name,
        location_lat=payload.location_lat,
        location_lng=payload.location_lng,
    )
    db.add(depot)
    try:
        db.flush()
        manager.depot = depot
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Depot code or another database constraint conflicts with this depot assignment.",
        ) from None

    db.refresh(depot)
    return depot


@router.delete(
    "/depots/{depot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_depot(
    depot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    depot = db.get(Depot, depot_id)
    if depot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Depot not found.",
        )

    references = (
        ("vehicles", select(Vehicle.id).where(Vehicle.depot_id == depot.id)),
        ("routes", select(Route.id).where(Route.depot_id == depot.id)),
        ("users", select(User.id).where(User.depot_id == depot.id)),
        ("incidents", select(Incident.id).where(Incident.depot_id == depot.id)),
    )
    for label, statement in references:
        if db.scalar(statement.limit(1)) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Depot cannot be deleted while it is referenced by {label}.",
            )

    db.delete(depot)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Depot is referenced by another operational record and cannot be deleted.",
        ) from None

