import json
from datetime import time
from typing import Any, Dict, List, Optional

from .database import Course, Schedule, SessionLocal


def get_courses_by_filters(
    day_of_week: Optional[str] = None,
    start_time_after: Optional[time] = None,
    end_time_before: Optional[time] = None,
    course_prefix: Optional[str] = None,
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
            query = query.filter(Schedule.day_of_week.ilike(f"%{day_of_week}%"))

        if start_time_after:
            query = query.filter(Schedule.start_time >= start_time_after)

        if end_time_before:
            query = query.filter(Schedule.end_time <= end_time_before)

        if course_prefix:
            query = query.filter(Course.course_code.startswith(course_prefix))

        return query.all()

    finally:
        db.close()


def get_courses_by_department(department: str) -> List[Course]:
    """Get all courses for a specific department prefix"""
    db = SessionLocal()
    try:
        return db.query(Course).filter(Course.course_prefix == department.upper()).all()
    finally:
        db.close()


def get_departments() -> List[str]:
    """Get list of all unique department prefixes"""
    db = SessionLocal()
    try:
        return [r[0] for r in db.query(Course.course_prefix).distinct().all()]
    finally:
        db.close()


def get_in_person_courses_by_department(department: str) -> List[Course]:
    """
    Get all in-person courses for a specific department that have schedules

    Args:
        department: Department prefix (e.g., "HOSF")

    Returns:
        List of courses matching criteria
    """
    db = SessionLocal()
    try:
        return (
            db.query(Course)
            .join(Course.schedules)  # Only courses with schedules
            .filter(Course.course_prefix == department.upper(), Course.course_delivery_type == "On Campus")
            .distinct()  # Avoid duplicates if course has multiple schedules
            .order_by(Course.course_number)  # Sort by course number
            .all()
        )
    finally:
        db.close()


def course_to_dict(course: Course) -> Dict[str, Any]:
    """Convert a course and its schedules to a dictionary"""
    return {
        "course_code": course.course_code,
        "course_prefix": course.course_prefix,
        "course_number": course.course_number,
        "course_name": course.course_name,
        "course_delivery_type": course.course_delivery_type,
        "prereqs": course.prereqs,
        "hours": course.hours,
        "fees": course.fees,
        "course_description": course.course_description,
        "course_link": course.course_link,
        "schedules": [
            {
                "start_date": schedule.start_date.isoformat() if schedule.start_date else None,
                "end_date": schedule.end_date.isoformat() if schedule.end_date else None,
                "day_of_week": schedule.day_of_week,
                "start_time": schedule.start_time.isoformat() if schedule.start_time else None,
                "end_time": schedule.end_time.isoformat() if schedule.end_time else None,
            }
            for schedule in course.schedules
        ],
    }


def get_in_person_courses_by_department_json(department: str, output_file: Optional[str] = None) -> str:
    """
    Get all in-person courses for a specific department as JSON

    Args:
        department: Department prefix (e.g., "HOSF")
        output_file: Optional file path to save JSON output

    Returns:
        JSON string of courses
    """
    db = SessionLocal()
    try:
        courses = (
            db.query(Course)
            .join(Course.schedules)
            .filter(Course.course_prefix == department.upper(), Course.course_delivery_type == "On Campus")
            .distinct()
            .order_by(Course.course_number)
            .all()
        )

        # Convert courses to dictionaries
        courses_data = [course_to_dict(course) for course in courses]

        # Convert to JSON
        json_data = json.dumps(courses_data, indent=2)

        # Save to file if specified
        if output_file:
            with open(output_file, "w") as f:
                f.write(json_data)

        return json_data

    finally:
        db.close()


def get_evening_courses_by_days_json(
    department: str, days: List[str], after_time: time, output_file: Optional[str] = None
) -> str:
    """
    Get courses for specific days after a certain time

    Args:
        department: Department prefix (e.g., "HOSF")
        days: List of days to search for (e.g., ["Tuesday", "Friday"])
        after_time: Only include courses starting after this time
        output_file: Optional file path to save JSON output

    Returns:
        JSON string of matching courses
    """
    db = SessionLocal()
    try:
        courses = (
            db.query(Course)
            .join(Course.schedules)
            .filter(
                Course.course_prefix == department.upper(),
                Course.course_delivery_type == "On Campus",
                Schedule.start_time >= after_time,
            )
            .filter(
                # Match any of the specified days
                Schedule.day_of_week.ilike(f"%{days[0]}%")
                if len(days) == 1
                # Use OR for multiple days
                else Schedule.day_of_week.ilike(f"%{days[0]}%") | Schedule.day_of_week.ilike(f"%{days[1]}%")
            )
            .distinct()
            .order_by(Course.course_number)
            .all()
        )

        # Convert courses to dictionaries
        courses_data = [course_to_dict(course) for course in courses]

        # Convert to JSON
        json_data = json.dumps(courses_data, indent=2)

        # Save to file if specified
        if output_file:
            with open(output_file, "w") as f:
                f.write(json_data)

        return json_data

    finally:
        db.close()


def get_evening_courses_summary_json(
    department: str, days: List[str], after_time: time, output_file: Optional[str] = None
) -> str:
    """
    Get summary of courses for specific days after a certain time

    Args:
        department: Department prefix (e.g., "HOSF")
        days: List of days to search for (e.g., ["Tuesday", "Friday"])
        after_time: Only include courses starting after this time
        output_file: Optional file path to save JSON output

    Returns:
        JSON string of matching courses summary with relevant schedules
    """
    db = SessionLocal()
    try:
        courses = (
            db.query(Course)
            .join(Course.schedules)
            .filter(
                Course.course_prefix == department.upper(),
                Course.course_delivery_type == "On Campus",
                Schedule.start_time >= after_time,
            )
            .filter(
                Schedule.day_of_week.ilike(f"%{days[0]}%")
                if len(days) == 1
                else Schedule.day_of_week.ilike(f"%{days[0]}%") | Schedule.day_of_week.ilike(f"%{days[1]}%")
            )
            .distinct()
            .order_by(Course.course_number)
            .all()
        )

        # Convert to simplified format with matching schedules
        courses_data = []
        for course in courses:
            # Filter schedules to only those matching our criteria
            matching_schedules = [
                {
                    "day": schedule.day_of_week,
                    "time": schedule.start_time.strftime("%I:%M %p") if schedule.start_time else None,
                    "start_date": schedule.start_date.strftime("%Y-%m-%d") if schedule.start_date else None,
                    "end_date": schedule.end_date.strftime("%Y-%m-%d") if schedule.end_date else None,
                }
                for schedule in course.schedules
                if schedule.start_time >= after_time
                and any(day.lower() in schedule.day_of_week.lower() for day in days)
            ]

            if matching_schedules:  # Only include if there are matching schedules
                courses_data.append(
                    {
                        "course_code": course.course_code,
                        "course_name": course.course_name,
                        "course_link": course.course_link,
                        "matching_schedules": matching_schedules,
                    }
                )

        # Convert to JSON
        json_data = json.dumps(courses_data, indent=2)

        # Save to file if specified
        if output_file:
            with open(output_file, "w") as f:
                f.write(json_data)

        return json_data

    finally:
        db.close()
