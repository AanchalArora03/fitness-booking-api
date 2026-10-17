from sqlalchemy import select
from sqlalchemy.orm import Session

from models.fitness_class import FitnessClass


def create_class(
    db: Session,
    *,
    name: str,
    date_time: str,
    instructor: str,
    available_slots: int,
) -> FitnessClass:
    """Insert a class with a normalized IST timestamp; the service commits."""
    fitness_class = FitnessClass(
        name=name,
        date_time=date_time,
        instructor=instructor,
        available_slots=available_slots,
    )
    db.add(fitness_class)
    db.flush()
    return fitness_class


def get_upcoming_classes(
    db: Session, *, now_ist: str
) -> list[FitnessClass]:
    """List future classes using IST ISO timestamps with matching precision."""
    statement = (
        select(FitnessClass)
        .where(FitnessClass.date_time > now_ist)
        .order_by(FitnessClass.date_time, FitnessClass.id)
    )
    return list(db.scalars(statement).all())
