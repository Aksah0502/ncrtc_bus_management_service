
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import require_roles
from app.core.authorization import ensure_depot_access, resolve_depot_filter
from app.db.session import get_db
from app.modules.fleet.models import Depot
from app.modules.routes.models import Route, RouteStop, Stop
from app.modules.routes.schemas import (
    RouteCreate,
    RouteDetailResponse,
    RoutePatch,
    RouteResponse,
    StopResponse,
)
from app.modules.users.models import User

router = APIRouter(prefix="/routes", tags=["Routes"])


def validate_route_stops(db: Session, stops):
    stop_ids = [item.stop_id for item in stops]

    if len(stop_ids) != len(set(stop_ids)):
        raise HTTPException(
            status_code=422,
            detail="A stop cannot appear more than once in a route.",
        )

    existing_ids = set(
        db.scalars(select(Stop.id).where(Stop.id.in_(stop_ids))).all()
    )
    missing_ids = set(stop_ids) - existing_ids

    if missing_ids:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown stop IDs: {sorted(missing_ids)}",
        )


def replace_route_stops(db: Session, route: Route, stops):
    validate_route_stops(db, stops)
    route.route_stops.clear()
    db.flush()

    for item in stops:
        route.route_stops.append(
            RouteStop(
                sequence=item.sequence,
                stop_id=item.stop_id,
                planned_offset_min=item.planned_offset_min,
            )
        )


@router.get("", response_model=list[RouteResponse])
def list_routes(
    depot_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "depot_manager")
    ),
):
    allowed_depot_id = resolve_depot_filter(current_user, depot_id)
    statement = select(Route).order_by(Route.id)

    if allowed_depot_id is not None:
        statement = statement.where(Route.depot_id == allowed_depot_id)

    return db.scalars(statement).all()


@router.get("/stops", response_model=list[StopResponse])
def list_stops(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "depot_manager")
    ),
):
    return db.scalars(select(Stop).order_by(Stop.name, Stop.id)).all()


@router.get("/{route_id}", response_model=RouteDetailResponse)
def get_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "depot_manager")
    ),
):
    route = db.scalar(
        select(Route)
        .options(selectinload(Route.route_stops).selectinload(RouteStop.stop))
        .where(Route.id == route_id)
    )

    if route is None:
        raise HTTPException(status_code=404, detail="Route not found.")

    ensure_depot_access(current_user, route.depot_id)
    return route


@router.post(
    "",
    response_model=RouteDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_route(
    payload: RouteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    if db.get(Depot, payload.depot_id) is None:
        raise HTTPException(status_code=422, detail="Depot not found.")

    validate_route_stops(db, payload.route_stops)

    route = Route(
        code=payload.code,
        name=payload.name,
        depot_id=payload.depot_id,
    )

    for item in payload.route_stops:
        route.route_stops.append(
            RouteStop(
                sequence=item.sequence,
                stop_id=item.stop_id,
                planned_offset_min=item.planned_offset_min,
            )
        )

    db.add(route)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Route code already exists or a database constraint was violated.",
        ) from None

    return db.scalar(
        select(Route)
        .options(selectinload(Route.route_stops).selectinload(RouteStop.stop))
        .where(Route.id == route.id)
    )


@router.patch("/{route_id}", response_model=RouteDetailResponse)
def update_route(
    route_id: int,
    payload: RoutePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    route = db.scalar(
        select(Route)
        .options(selectinload(Route.route_stops))
        .where(Route.id == route_id)
    )

    if route is None:
        raise HTTPException(status_code=404, detail="Route not found.")

    changes = payload.model_dump(exclude_unset=True)

    for field in ("code", "name"):
        if field in changes:
            if changes[field] is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"{field} cannot be null.",
                )
            setattr(route, field, changes[field])

    if "route_stops" in changes:
        if changes["route_stops"] is None:
            raise HTTPException(
                status_code=422,
                detail="route_stops cannot be null.",
            )
        replace_route_stops(db, route, payload.route_stops or [])

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Route code already exists or a database constraint was violated.",
        ) from None

    return db.scalar(
        select(Route)
        .options(selectinload(Route.route_stops).selectinload(RouteStop.stop))
        .where(Route.id == route.id)
    )


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    route = db.get(Route, route_id)

    if route is None:
        raise HTTPException(status_code=404, detail="Route not found.")

    db.delete(route)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Route cannot be deleted because it is referenced by existing records.",
        ) from None
