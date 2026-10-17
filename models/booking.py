from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from models.fitness_class import FitnessClass


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (UniqueConstraint("user_id", "class_id", name="unique_user_class"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("fitness_classes.id"))
    client_name: Mapped[str] = mapped_column(String(100))
    client_email: Mapped[str] = mapped_column(String(255))
    fitness_class: Mapped[FitnessClass] = relationship()
