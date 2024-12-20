import json
import os
from datetime import datetime, time
from typing import List
from pathlib import Path

from .database import Course, Schedule, init_db, SessionLocal

def parse_time(time_str: str) -> time:
    """Convert time string (e.g., '6:15PM') to time object"""
    return datetime.strptime(time_str, '%I:%M%p').time()

def parse_date(date_str: str) -> datetime:
    """Convert date string (e.g., '07Nov2024') to datetime object"""
    return datetime.strptime(date_str, '%d%b%Y')

def load_course_data(json_dir: str):
    """Load course data from JSON files into database"""
    db = SessionLocal()
    
    try:
        # Get all JSON files in the directory
        json_files = Path(json_dir).glob('*.json')
        
        for json_file in json_files:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Create course
            course = Course(
                course_code=data['course_code'],
                course_name=data['course_name'],
                course_delivery_type=data.get('course_delivery_type'),
                prereqs=data.get('prereqs'),
                hours=data.get('hours'),
                fees=data.get('fees'),
                course_description=data.get('course_description'),
                course_link=data.get('course_link')
            )
            
            # Add schedules
            if 'schedules' in data:
                for schedule_data in data['schedules']:
                    schedule = Schedule(
                        start_date=parse_date(schedule_data['start_date']),
                        end_date=parse_date(schedule_data['end_date']),
                        day_of_week=schedule_data['day_or_days_of_week'],
                        start_time=parse_time(schedule_data['start_time']),
                        end_time=parse_time(schedule_data['end_time'])
                    )
                    course.schedules.append(schedule)
            
            db.add(course)
        
        db.commit()
    
    except Exception as e:
        print(f"Error loading data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Initialize database
    init_db()
    
    # Load data from JSON files
    json_dir = "data/course_data"
    load_course_data(json_dir) 