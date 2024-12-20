from sqlalchemy import extract
from datetime import time
from typing import List, Optional

from .database import Course, Schedule, SessionLocal

def get_courses_by_filters(
    day_of_week: Optional[str] = None,
    start_time_after: Optional[time] = None,
    end_time_before: Optional[time] = None,
    course_prefix: Optional[str] = None
) -> List[Course]:
    """
    Query courses with various filters
    
    Args:
        day_of_week: Day of the week (e.g., "M" or "Monday")
        start_time_after: Only return courses starting after this time
        end_time_before: Only return courses ending before this time
        course_prefix: Filter by course code prefix (e.g., "HOSF")
    """
    db = SessionLocal()
    try:
        query = db.query(Course).join(Course.schedules)
        
        if day_of_week:
            query = query.filter(Schedule.day_of_week.ilike(f'%{day_of_week}%'))
        
        if start_time_after:
            query = query.filter(Schedule.start_time >= start_time_after)
            
        if end_time_before:
            query = query.filter(Schedule.end_time <= end_time_before)
            
        if course_prefix:
            query = query.filter(Course.course_code.startswith(course_prefix))
        
        return query.all()
    
    finally:
        db.close() 