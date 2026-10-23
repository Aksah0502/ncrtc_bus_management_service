from fastapi import HTTPException, status

from app.modules.users.models import User


SYSTEM_WIDE_ROLES = {
    "admin",
    "control_operator",
}

DEPOT_SCOPED_ROLES = {
    "driver",
    "depot_manager",
}


def resolve_depot_filter(
    current_user: User,
    requested_depot_id: int | None = None,
) -> int | None:
    """
    Resolve the permitted depot filter for an operational list.

    System-wide roles may use an optional depot filter.
    Depot-scoped roles are restricted to their assigned depot.
    """
    role = (current_user.role or "").lower()

    if role in SYSTEM_WIDE_ROLES:
        return requested_depot_id

    if role in DEPOT_SCOPED_ROLES:
        assigned_depot_id = current_user.depot_id

        if assigned_depot_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account has no assigned depot.",
            )

        if (
            requested_depot_id is not None
            and requested_depot_id != assigned_depot_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot access another depot's data.",
            )

        return assigned_depot_id

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This role cannot access this operational resource.",
    )


def ensure_depot_access(
    current_user: User,
    resource_depot_id: int | None,
) -> None:
    """Check depot access before returning a specific resource."""
    role = (current_user.role or "").lower()

    if role in SYSTEM_WIDE_ROLES:
        return

    if (
        role in DEPOT_SCOPED_ROLES
        and current_user.depot_id is not None
        and resource_depot_id == current_user.depot_id
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You cannot access this depot's resource.",
    )