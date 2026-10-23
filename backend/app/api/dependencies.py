from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, oauth2_scheme
from app.db.session import get_db
from app.modules.users.models import User


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve a valid bearer token to its current database user."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        raise unauthorized from None

    subject = payload.get("sub")

    if not isinstance(subject, str) or not subject.isdecimal():
        raise unauthorized

    user = db.get(User, int(subject))

    if user is None:
        raise unauthorized

    return user


def require_roles(*allowed_roles: str) -> Callable[..., User]:
    """Return a dependency that allows only the specified roles."""
    normalized_roles = {
        role.lower() for role in allowed_roles
    }

    def check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_role = (current_user.role or "").lower()

        if user_role not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )

        return current_user

    return check_role