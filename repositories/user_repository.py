from sqlalchemy import select
from sqlalchemy.orm import Session

from models.user import User


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Find the account identified by a validated token."""
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    """Find a user by email, returning None when no account exists."""
    return db.scalar(select(User).where(User.email == email))


def create_user(
    db: Session, *, name: str, email: str, hashed_password: str
) -> User:
    """Insert a user; the calling service must commit the transaction."""
    user = User(name=name, email=email, hashed_password=hashed_password)
    db.add(user)
    db.flush()
    return user
