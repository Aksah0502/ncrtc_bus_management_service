from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError

from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


def hash_password(password: str) -> str:
    """Hash a password before saving it to the database."""
    password_bytes = password.encode("utf-8")

    # bcrypt supports passwords up to 72 bytes.
    if len(password_bytes) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes.")

    password_hash = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(),
    )

    return password_hash.decode("utf-8")


def verify_password(
    plain_password: str,
    stored_hash: str,
) -> bool:
    """Compare a login password with its stored bcrypt hash."""
    password_bytes = plain_password.encode("utf-8")

    if len(password_bytes) > 72:
        return False

    try:
        return bcrypt.checkpw(
            password_bytes,
            stored_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # A malformed stored hash must never authenticate a user.
        return False


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT whose subject is the user's database ID."""
    now = datetime.now(timezone.utc)

    expires_at = now + (
        expires_delta
        or timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    """Verify the JWT signature and required claims."""
    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "iat", "exp"]},
    )