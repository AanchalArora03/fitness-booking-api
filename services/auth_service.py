from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from core.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from core.security import hash_password, verify_password
from models.user import User
from repositories.user_repository import create_user, get_user_by_email
from schemas.auth import SignupRequest

_DUMMY_HASH = hash_password("dummy-password-for-timing")


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Verify credentials without revealing whether the account exists."""
    user = get_user_by_email(db, email.lower())
    valid = verify_password(password, user.hashed_password if user else _DUMMY_HASH)
    if user is None or not valid:
        raise InvalidCredentialsError()
    return user


def signup(db: Session, data: SignupRequest) -> User:
    """Register an account and commit it, or roll back a failed database write."""
    email = str(data.email).lower()
    if get_user_by_email(db, email) is not None:
        raise EmailAlreadyRegisteredError()

    hashed_password = hash_password(data.password)
    try:
        user = create_user(
            db,
            name=data.name,
            email=email,
            hashed_password=hashed_password,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Another request may have registered the email after our first lookup.
        if get_user_by_email(db, email) is not None:
            raise EmailAlreadyRegisteredError() from exc
        raise
    except SQLAlchemyError:
        db.rollback()
        raise

    return user
