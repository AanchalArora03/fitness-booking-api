from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from models.user import User
from core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from core.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from core.security import create_access_token
from schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserResponse
from services.auth_service import authenticate_user, signup

router = APIRouter(tags=["Authentication"])


@router.get("/me", response_model=UserResponse)
def get_me(user: Annotated[User, Depends(get_current_user)]):
    """Return the authenticated user's public account details."""
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    """Authenticate with JSON credentials and return an expiring bearer token."""
    try:
        user = authenticate_user(db, str(data.email), data.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}
        ) from exc
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(data: SignupRequest, db: Annotated[Session, Depends(get_db)]):
    """Register a user and return public account details."""
    try:
        return signup(db, data)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
