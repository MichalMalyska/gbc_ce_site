import os

from dotenv import load_dotenv
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Time, create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create declarative base
Base = declarative_base()


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    course_code = Column(String, unique=True, nullable=False)
    course_prefix = Column(String(4), nullable=False, index=True)
    course_number = Column(String(10), nullable=False)
    course_name = Column(String, nullable=False)
    course_delivery_type = Column(String)
    prereqs = Column(String)
    hours = Column(String)
    fees = Column(String)
    course_description = Column(String)
    course_link = Column(String)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    # Relationship with schedules
    schedules = relationship("Schedule", back_populates="course", cascade="all, delete-orphan")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    day_of_week = Column(String, nullable=False)  # Store as comma-separated string
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)

    # Relationship with course
    course = relationship("Course", back_populates="schedules")


# Create all tables
def init_db():
    Base.metadata.create_all(engine)
    ensure_course_last_seen_column()


# Create session factory
SessionLocal = sessionmaker(bind=engine)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def drop_and_recreate_tables():
    """Drop all tables and recreate them"""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def ensure_course_last_seen_column():
    """Add the last_seen_at column for existing databases that predate the incremental sync path."""
    inspector = inspect(engine)
    if "courses" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("courses")}
    if "last_seen_at" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE courses "
                "ADD COLUMN last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL"
            )
        )
