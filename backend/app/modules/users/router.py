from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.modules.cms.models import Notice, NoticeRead
from app.modules.fleet.models import Depot
from app.modules.incidents.models import Incident, IncidentEvent
from app.modules.scheduling.models import Duty
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


def _has_user_history(db: Session, user_id: int) -> bool:
    checks = (
        select(Duty.id).where(
            or_(Duty.driver_id == user_id, Duty.conductor_id == user_id)
        ),
        select(Incident.id).where(
            or_(Incident.raised_by == user_id, Incident.assigned_to == user_id)
        ),
        select(IncidentEvent.id).where(IncidentEvent.actor_id == user_id),
        select(Notice.id).where(Notice.created_by == user_id),
        select(NoticeRead.notice_id).where(NoticeRead.user_id == user_id),
    )
    return any(db.scalar(statement.limit(1)) is not None for statement in checks)


@router.get("", response_model=list[UserResponse])
def list_users(
    role: str | None = Query(default=None, min_length=1, max_length=30),
    depot_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    statement = select(User).order_by(User.id)
    if role is not None:
        statement = statement.where(User.role == role)
    if depot_id is not None:
        statement = statement.where(User.depot_id == depot_id)
    return db.scalars(statement).all()


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    if db.scalar(select(User.id).where(User.username == payload.username)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already in use.",
        )

    if payload.driving_license_number and db.scalar(
        select(User.id).where(
            User.driving_license_number == payload.driving_license_number
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Driving licence number is already in use.",
        )

    if payload.role == "control_operator" and payload.depot_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Control-room operators cannot be assigned to a depot.",
        )

    if payload.role == "driver" and payload.depot_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Drivers must be assigned to a depot.",
        )

    if payload.depot_id is not None and db.get(Depot, payload.depot_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Depot not found.",
        )

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        depot_id=payload.depot_id,
        phone=payload.phone,
        driving_license_number=payload.driving_license_number,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username, licence number, or another database constraint conflicts with this user.",
        ) from None

    db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The authenticated administrator cannot delete their own account.",
        )

    if user.role == "admin":
        admin_count = db.scalar(
            select(func.count(User.id)).where(User.role == "admin")
        )
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The final administrator account cannot be deleted.",
            )

    if user.role == "depot_manager" and user.depot_id is not None:
        another_manager = db.scalar(
            select(User.id).where(
                User.depot_id == user.depot_id,
                User.role == "depot_manager",
                User.id != user.id,
            ).limit(1)
        )
        if another_manager is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete the only depot manager assigned to this depot.",
            )

    if _has_user_history(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is referenced by operational or historical records and cannot be deleted.",
        )

    db.delete(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is referenced by another record and cannot be deleted.",
        ) from None
