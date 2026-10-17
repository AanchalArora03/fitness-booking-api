from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.fitness_class import FitnessClass
from repositories import class_repository
from schemas.fitness_class import ClassCreate

IST = ZoneInfo("Asia/Kolkata")


def format_ist(value: datetime) -> str:
    """Normalize aware timestamps for consistent SQLite storage and comparison."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Class date must include a timezone.")
    return value.astimezone(IST).isoformat(timespec="microseconds")


def create_class(db: Session, data: ClassCreate) -> FitnessClass:
    """Save validated class details in IST and commit the transaction."""
    date_time = format_ist(data.date_time)
    if data.date_time <= datetime.now(IST):
        raise ValueError("Class date must be in the future.")
    try:
        fitness_class = class_repository.create_class(
            db,
            name=data.name,
            date_time=date_time,
            instructor=data.instructor,
            available_slots=data.available_slots,
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return fitness_class


def get_upcoming_classes(db: Session) -> list[FitnessClass]:
    """Return future classes ordered by their normalized IST start time."""
    return class_repository.get_upcoming_classes(
        db, now_ist=format_ist(datetime.now(IST))
    )
