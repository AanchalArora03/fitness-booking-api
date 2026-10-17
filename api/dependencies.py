from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from core.security import decode_access_token
from db.session import SessionLocal
from models.user import User
from repositories.user_repository import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Require a valid bearer token belonging to an existing account."""
    unauthorized = HTTPException(
        status_code=401,
        detail="Invalid or expired authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise unauthorized from exc
    user = get_user_by_id(db, user_id)
    if user is None:
        raise unauthorized
    return user
