from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class FitnessClass(Base):
    __tablename__ = "fitness_classes"
    __table_args__ = (
        CheckConstraint(
            "available_slots >= 0",
            name="check_available_slots_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    date_time: Mapped[str] = mapped_column(String(40), index=True)
    instructor: Mapped[str] = mapped_column(String(100))
    available_slots: Mapped[int] = mapped_column(Integer)