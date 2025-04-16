from datetime import datetime
from typing import Any, Dict, List, Optional


def filter_courses_by_subject(courses: List[Dict[str, Any]], subject: str) -> List[Dict[str, Any]]:
    """Filter courses by subject keyword in course code or name"""
    return [
        course
        for course in courses
        if subject.lower() in course.get("course_code", "").lower()
        or subject.lower() in course.get("course_name", "").lower()
    ]


def filter_courses_by_day(courses: List[Dict[str, Any]], day: str) -> List[Dict[str, Any]]:
    """Filter courses by specific day of the week"""
    filtered_courses = []
    day = day.lower()

    for course in courses:
        schedules = course.get("schedules", [])
        if not schedules:
            continue

        for schedule in schedules:
            if isinstance(schedule, dict):
                days = schedule.get("day_or_days_of_week", "").lower()
                if day in days:
                    filtered_courses.append(course)
                    break

    return filtered_courses


def filter_courses_by_time(
    courses: List[Dict[str, Any]], after_time: Optional[str] = None, before_time: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filter courses by time range
    Times should be in 24-hour format HH:MM
    """
    filtered_courses = []

    def parse_time(time_str: str) -> datetime:
        """Convert 12-hour time to datetime object"""
        try:
            return datetime.strptime(time_str, "%I:%M %p")
        except ValueError:
            return datetime.strptime(time_str, "%H:%M")

    after_dt = parse_time(after_time) if after_time else None
    before_dt = parse_time(before_time) if before_time else None

    for course in courses:
        schedules = course.get("schedules", [])
        if not schedules:
            continue

        for schedule in schedules:
            if isinstance(schedule, dict):
                start_time = schedule.get("start_time")
                if not start_time:
                    continue

                try:
                    start_dt = parse_time(start_time)

                    matches_after = True if after_dt is None else start_dt >= after_dt
                    matches_before = True if before_dt is None else start_dt <= before_dt

                    if matches_after and matches_before:
                        filtered_courses.append(course)
                        break
                except ValueError:
                    continue

    return filtered_courses


def filter_courses(
    courses: List[Dict[str, Any]],
    subject: Optional[str] = None,
    day: Optional[str] = None,
    after_time: Optional[str] = None,
    before_time: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Apply all filters in sequence"""
    filtered = courses

    if subject:
        filtered = filter_courses_by_subject(filtered, subject)
    if day:
        filtered = filter_courses_by_day(filtered, day)
    if after_time or before_time:
        filtered = filter_courses_by_time(filtered, after_time, before_time)

    return filtered
