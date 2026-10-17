from datetime import datetime

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from core.exceptions import BookingConflictError, ClassNotFoundError
from models.fitness_class import FitnessClass
from repositories import booking_repository
from schemas.booking import BookingCreate
from services.class_service import IST, format_ist


def book_class(db: Session, user_id: int, data: BookingCreate):
    """Reserve capacity and insert ownership in one transaction."""
    try:
        reserved = booking_repository.reserve_slot(
            db, data.class_id, format_ist(datetime.now(IST))
        )
        if not reserved:
            if db.get(FitnessClass, data.class_id) is None:
                raise ClassNotFoundError("Class not found.")
            raise BookingConflictError("Class has started or has no available slots.")
        booking = booking_repository.create_booking(
            db, user_id=user_id, class_id=data.class_id,
            client_name=data.client_name, client_email=str(data.client_email),
        )
        db.commit()
        return booking
    except IntegrityError as exc:
        db.rollback()
        # Capacity changes are rolled back along with a duplicate booking.
        raise BookingConflictError("You have already booked this class.") from exc
    except (SQLAlchemyError, ClassNotFoundError, BookingConflictError):
        db.rollback()
        raise


def get_user_bookings(db: Session, user_id: int):
    return booking_repository.get_bookings(db, user_id)
