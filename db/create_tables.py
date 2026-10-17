from db.base import Base
from db.session import engine
from models.user import User
from models.fitness_class import FitnessClass
from models.booking import Booking


def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database tables created successfully.")
