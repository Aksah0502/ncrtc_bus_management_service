
from datetime import date, timedelta, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.authorization import resolve_depot_filter
from app.db.session import get_db
from app.modules.fleet.models import Depot, Vehicle
from app.modules.routes.models import Route
from app.modules.scheduling.models import Duty
from app.modules.scheduling.schemas import DutyCreate, DutyPatch, DutyResponse
from app.modules.users.models import User

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])


@router.get("/duties", response_model=list[DutyResponse])
def list_duties(
    depot_id: int | None = Query(default=None, gt=0),
    service_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed_depot_id = resolve_depot_filter(current_user, depot_id)

    statement = select(Duty).join(
        Vehicle, Duty.vehicle_id == Vehicle.id
    ).order_by(Duty.id)

    if allowed_depot_id is not None:
        statement = statement.where(Vehicle.depot_id == allowed_depot_id)

    if (current_user.role or "").lower() == "driver":
        statement = statement.where(Duty.driver_id == current_user.id)

    if service_date is not None:
        statement = statement.where(Duty.service_date == service_date)

    return db.scalars(statement).all()

duties_router = APIRouter(prefix="/duties", tags=["Duties"])


@duties_router.get("/today", response_model=list[DutyResponse])
def get_today_duty(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("driver")),
):
    today = date.today()

    statement = select(Duty).where(
        Duty.driver_id == current_user.id,
        Duty.service_date == today,
        Duty.status == "published",
    ).order_by(Duty.start_time)

    return db.scalars(statement).all()


@duties_router.get("", response_model=list[DutyResponse])
def get_weekly_roster(
    week_start: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("depot_manager")),
):
    depot_id = resolve_depot_filter(current_user)

    week_end = week_start + timedelta(days=7)

    statement = (
        select(Duty)
        .join(Vehicle, Duty.vehicle_id == Vehicle.id)
        .where(
            Vehicle.depot_id == depot_id,
            Duty.service_date >= week_start,
            Duty.service_date < week_end,
        )
        .order_by(Duty.service_date, Duty.start_time)
    )

    return db.scalars(statement).all()



def validate_assignment(db: Session, payload, depot_id: int):
    vehicle = db.get(Vehicle, payload.vehicle_id)
    if vehicle is None or vehicle.depot_id != depot_id:
        raise HTTPException(
            status_code=422,
            detail="Vehicle not found in your depot.",
        )

    route = db.get(Route, payload.route_id)
    if route is None or route.depot_id != depot_id:
        raise HTTPException(
            status_code=422,
            detail="Route not found in your depot.",
        )

    driver = db.get(User, payload.driver_id)
    if (
        driver is None
        or (driver.role or "").lower() != "driver"
        or driver.depot_id != depot_id
    ):
        raise HTTPException(
            status_code=422,
            detail="Driver not found in your depot.",
        )

    if payload.conductor_id is not None:
        conductor = db.get(User, payload.conductor_id)
        if (
            conductor is None
            or (conductor.role or "").lower() != "conductor"
            or conductor.depot_id != depot_id
        ):
            raise HTTPException(
                status_code=422,
                detail="Conductor not found in your depot.",
            )


@duties_router.post("", response_model=DutyResponse, status_code=201)
def create_duty(
    payload: DutyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("depot_manager")),
):
    depot_id = resolve_depot_filter(current_user)
    validate_assignment(db, payload, depot_id)

    duty = Duty(
        **payload.model_dump(),
        status="draft",
    )
    db.add(duty)

    try:
        db.commit()
        db.refresh(duty)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Duty conflicts with a database constraint.",
        ) from None

    return duty


@duties_router.patch("/{duty_id}", response_model=DutyResponse)
def update_duty(
    duty_id: int,
    payload: DutyPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("depot_manager")),
):
    depot_id = resolve_depot_filter(current_user)

    duty = db.scalar(
        select(Duty)
        .join(Vehicle, Duty.vehicle_id == Vehicle.id)
        .where(
            Duty.id == duty_id,
            Vehicle.depot_id == depot_id,
        )
    )

    if duty is None:
        raise HTTPException(status_code=404, detail="Duty not found.")

    if duty.status.lower() == "published":
        raise HTTPException(
            status_code=409,
            detail="Published duties cannot be edited.",
        )

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=422, detail="No fields supplied.")

    values = {
        "vehicle_id": duty.vehicle_id,
        "driver_id": duty.driver_id,
        "conductor_id": duty.conductor_id,
        "route_id": duty.route_id,
        "service_date": duty.service_date,
        "start_time": duty.start_time,
        "end_time": duty.end_time,
    }
    values.update(changes)

    if values["start_time"] is None or values["end_time"] is None:
        raise HTTPException(
            status_code=422,
            detail="Start and end times cannot be null.",
        )

    if values["end_time"] <= values["start_time"]:
        raise HTTPException(
            status_code=422,
            detail="end_time must be later than start_time.",
        )

    validate_assignment(db, type("Assignment", (), values)(), depot_id)

    for field, value in changes.items():
        if value is None and field != "conductor_id":
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null.",
            )
        setattr(duty, field, value)

    try:
        db.commit()
        db.refresh(duty)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Duty conflicts with a database constraint.",
        ) from None

    return duty



@duties_router.post("/{duty_id}/publish", response_model=DutyResponse)
def publish_duty(
    duty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("depot_manager")),
):
    depot_id = resolve_depot_filter(current_user)

    duty = db.scalar(
        select(Duty)
        .join(Vehicle, Duty.vehicle_id == Vehicle.id)
        .where(
            Duty.id == duty_id,
            Vehicle.depot_id == depot_id,
        )
    )

    if duty is None:
        raise HTTPException(status_code=404, detail="Duty not found.")

    if duty.status.lower() != "draft":
        raise HTTPException(
            status_code=409,
            detail="Only draft duties can be published.",
        )

    duty.status = "published"

    try:
        db.commit()
        db.refresh(duty)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Unable to publish duty.",
        ) from None

    return duty


@duties_router.post("/{duty_id}/acknowledge", response_model=DutyResponse)
def acknowledge_duty(
    duty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("driver")),
):
    duty = db.get(Duty, duty_id)

    if duty is None or duty.driver_id != current_user.id:
        raise HTTPException(status_code=404, detail="Duty not found.")

    if duty.status.lower() != "published":
        raise HTTPException(
            status_code=409,
            detail="Only published duties can be acknowledged.",
        )

    if duty.ack_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Duty has already been acknowledged.",
        )

    duty.ack_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(duty)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Unable to acknowledge duty.",
        ) from None

    return duty
