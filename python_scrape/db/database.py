from sqlalchemy import create_engine, Column, Integer, String, Time, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/course_scheduler")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create declarative base
Base = declarative_base()

class Course(Base):
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True)
    course_code = Column(String, unique=True, nullable=False)
    course_name = Column(String, nullable=False)
    course_delivery_type = Column(String)
    prereqs = Column(String)
    hours = Column(String)
    fees = Column(String)
    course_description = Column(String)
    course_link = Column(String)
    
    # Relationship with schedules
    schedules = relationship("Schedule", back_populates="course")

class Schedule(Base):
    __tablename__ = 'schedules'
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    day_of_week = Column(String, nullable=False)  # Store as comma-separated string
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    
    # Relationship with course
    course = relationship("Course", back_populates="schedules")

# Create all tables
def init_db():
    Base.metadata.create_all(engine)

# Create session factory
SessionLocal = sessionmaker(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 