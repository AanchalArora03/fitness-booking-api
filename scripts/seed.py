"""Add sample future classes: python -m scripts.seed."""
from datetime import datetime, timedelta

from sqlalchemy import select

from db.create_tables import init_db
from db.session import SessionLocal
from models.fitness_class import FitnessClass
from schemas.fitness_class import ClassCreate
from services.class_service import IST, create_class, format_ist


def seed():
    init_db()
    now = datetime.now(IST)
    with SessionLocal() as db:
        for day, (name, instructor, slots) in enumerate(
            [('Yoga Flow', 'Asha Sharma', 20), ('Zumba', 'Riya Patel', 15), ('HIIT Session', 'Arjun Rao', 10)],
            start=1,
        ):
            exists = db.scalar(select(FitnessClass.id).where(
                FitnessClass.name == name, FitnessClass.date_time > format_ist(now)
            ))
            if exists is None:
                create_class(db, ClassCreate(
                    name=name, instructor=instructor, availableSlots=slots,
                    dateTime=(now + timedelta(days=day)).replace(hour=10, minute=0, second=0, microsecond=0),
                ))
    print('Sample upcoming classes are ready.')


if __name__ == '__main__':
    seed()
