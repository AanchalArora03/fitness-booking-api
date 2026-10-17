from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from models.booking import Booking
from models.fitness_class import FitnessClass


def reserve_slot(db: Session, class_id: int, now_ist: str) -> bool:
    """Atomically decrement only an upcoming class with remaining capacity."""
    result = db.execute(
        update(FitnessClass)
        .where(FitnessClass.id == class_id,
               FitnessClass.date_time > now_ist,
               FitnessClass.available_slots > 0)
        .values(available_slots=FitnessClass.available_slots - 1)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def create_booking(db: Session, **values) -> Booking:
    booking = Booking(**values)
    db.add(booking)
    db.flush()
    return booking


def get_bookings(db: Session, user_id: int) -> list[Booking]:
    return list(db.scalars(
        select(Booking).options(joinedload(Booking.fitness_class))
        .where(Booking.user_id == user_id).order_by(Booking.id.desc())
    ).all())
