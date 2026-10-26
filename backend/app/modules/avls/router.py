
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.authorization import resolve_depot_filter, ensure_depot_access
from app.db.session import get_db
from app.modules.avls.models import GPSPing
from app.modules.avls.schemas import (
    LiveLocationResponse,
    LiveDetailsResponse,
    LocationHistoryResponse,
)
from app.modules.fleet.models import Vehicle
from app.modules.routes.models import Route
from app.modules.scheduling.models import Duty
from app.modules.users.models import User

router = APIRouter(prefix="/vehicles", tags=["AVLS"])
AVLS_ROLES = ("control_operator", "depot_manager")
IST = ZoneInfo("Asia/Kolkata")


@router.get("/live-locations", response_model=list[LiveLocationResponse])
def live_locations(
    depot_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AVLS_ROLES)),
):
    allowed_depot_id = resolve_depot_filter(current_user, depot_id)

    latest_ping = (
        select(
            GPSPing.vehicle_id.label("vehicle_id"),
            func.max(GPSPing.ts).label("latest_ts"),
        )
        .group_by(GPSPing.vehicle_id)
        .subquery()
    )

    statement = (
        select(
            Vehicle.id.label("vehicle_id"),
            Vehicle.reg_no,
            Vehicle.depot_id,
            GPSPing.lat,
            GPSPing.lng,
            GPSPing.speed_kmh,
            GPSPing.ts,
        )
        .join(latest_ping, latest_ping.c.vehicle_id == Vehicle.id)
        .join(
            GPSPing,
            (GPSPing.vehicle_id == latest_ping.c.vehicle_id)
            & (GPSPing.ts == latest_ping.c.latest_ts),
        )
        .where(Vehicle.status == "active")
        .order_by(Vehicle.id)
    )

    if allowed_depot_id is not None:
        statement = statement.where(Vehicle.depot_id == allowed_depot_id)

    return [dict(row._mapping) for row in db.execute(statement).all()]


@router.get(
    "/{vehicle_id}/live-details",
    response_model=LiveDetailsResponse,
)
def live_details(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AVLS_ROLES)),
):
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found.")

    ensure_depot_access(current_user, vehicle.depot_id)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=30)

    pings = db.scalars(
        select(GPSPing)
        .where(
            GPSPing.vehicle_id == vehicle_id,
            GPSPing.ts >= cutoff,
            GPSPing.ts <= now,
        )
        .order_by(GPSPing.ts)
    ).all()

    local_today = datetime.now(IST).date()
    duty = db.scalar(
        select(Duty)
        .where(
            Duty.vehicle_id == vehicle_id,
            Duty.service_date == local_today,
            Duty.status == "published",
        )
        .order_by(Duty.start_time.desc())
        .limit(1)
    )

    driver = db.get(User, duty.driver_id) if duty else None
    route = db.get(Route, duty.route_id) if duty else None

    return {
        "vehicle_id": vehicle.id,
        "reg_no": vehicle.reg_no,
        "driver_name": driver.full_name if driver else None,
        "driver_phone": driver.phone if driver else None,
        "driver_driving_license_number": (
            driver.driving_license_number if driver else None
        ),
        "route_code": route.code if route else None,
        "route_name": route.name if route else None,
        "pings": pings,
    }


@router.get(
    "/{vehicle_id}/location-history",
    response_model=LocationHistoryResponse,
)
def location_history(
    vehicle_id: int,
    date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AVLS_ROLES)),
):
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found.")

    ensure_depot_access(current_user, vehicle.depot_id)

    start = datetime.combine(date, time.min, tzinfo=IST)
    end = start + timedelta(days=1)

    pings = db.scalars(
        select(GPSPing)
        .where(
            GPSPing.vehicle_id == vehicle_id,
            GPSPing.ts >= start,
            GPSPing.ts < end,
        )
        .order_by(GPSPing.ts)
    ).all()

    return {
        "vehicle_id": vehicle_id,
        "date": date,
        "pings": pings,
    }
