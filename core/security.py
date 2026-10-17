from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
)


password_hasher = PasswordHash.recommended()


def decode_access_token(token: str) -> int:
    """Validate the token and return its user ID; invalid tokens raise InvalidTokenError."""
    claims = jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "iat", "exp"]},
    )
    subject = claims["sub"]
    if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal():
        raise jwt.InvalidTokenError("Invalid subject")
    if len(subject) > 19 or not 0 < int(subject) <= 9223372036854775807:
        raise jwt.InvalidTokenError("Invalid user ID")
    return int(subject)


def hash_password(password: str) -> str:
    """Create an Argon2 password hash for storage."""
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Check a plain password against its stored hash."""
    return password_hasher.verify(password, hashed_password)


def create_access_token(user_id: int) -> str:
    """Issue a signed, expiring token identifying the authenticated user."""
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user_id), "iat": now,
         "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
