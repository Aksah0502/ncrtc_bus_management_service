from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.modules.auth.schemas import (
    CurrentUserResponse,
    TokenResponse,
)
from app.modules.users.models import User


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and obtain an access token",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate using username and password."""
    user = db.scalar(
        select(User).where(
            User.username == form_data.username
        )
    )

    if user is None or not verify_password(
        form_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=str(user.id),
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get the currently authenticated user",
)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> CurrentUserResponse:
    """Return safe profile fields for the logged-in user."""
    return CurrentUserResponse.model_validate(current_user)