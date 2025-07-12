#!/usr/bin/env python3
"""
Compare scraped JSON data with existing database data.
This script reads both sources and compares them without writing anything.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set

from .database import Course, Schedule, SessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def read_json_data(json_dir: str, test_mode: bool = False) -> Dict[str, dict]:
    """Read all JSON files and return a dictionary of course data"""
    json_files = list(Path(json_dir).glob("*.json"))
    
    if test_mode:
        json_files = json_files[:5]
        logger.info(f"TEST MODE: Reading only {len(json_files)} files")
    
    logger.info(f"Reading {len(json_files)} JSON files...")
    
    json_data = {}
    for json_file in json_files:
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                course_code = data.get("course_code", "")
                if course_code:
                    json_data[course_code] = data
        except Exception as e:
            logger.error(f"Error reading {json_file.name}: {e}")
    
    return json_data


def read_database_data() -> Dict[str, dict]:
    """Read all course data from database and return a dictionary"""
    db = SessionLocal()
    try:
        logger.info("Reading data from database...")
        
        # Get all courses with their schedules
        courses = db.query(Course).all()
        
        db_data = {}
        for course in courses:
            course_dict = {
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
                "schedules": []
            }
            
            # Add schedules
            for schedule in course.schedules:
                schedule_dict = {
                    "start_date": schedule.start_date.isoformat() if schedule.start_date else None,
                    "end_date": schedule.end_date.isoformat() if schedule.end_date else None,
                    "day_of_week": schedule.day_of_week,
                    "start_time": schedule.start_time.isoformat() if schedule.start_time else None,
                    "end_time": schedule.end_time.isoformat() if schedule.end_time else None,
                }
                course_dict["schedules"].append(schedule_dict)
            
            db_data[course.course_code] = course_dict
        
        return db_data
        
    finally:
        db.close()


def compare_data(json_data: Dict[str, dict], db_data: Dict[str, dict]) -> dict:
    """Compare JSON data with database data"""
    json_codes = set(json_data.keys())
    db_codes = set(db_data.keys())

    # Find differences
    only_in_json = json_codes - db_codes
    only_in_db = db_codes - json_codes
    in_both = json_codes & db_codes

    # --- Deep Schedule Comparison ---
    updated_courses = []
    for code in in_both:
        # Create a set of tuples for each schedule for easy comparison
        json_schedules_set = {
            (
                s.get("start_date"),
                s.get("end_date"),
                s.get("day_or_days_of_week"),
                s.get("start_time"),
                s.get("end_time"),
            )
            for s in json_data[code].get("schedules", [])
        }
        db_schedules_set = {
            (
                s.get("start_date"),
                s.get("end_date"),
                s.get("day_of_week"),
                s.get("start_time"),
                s.get("end_time"),
            )
            for s in db_data[code].get("schedules", [])
        }

        # If the sets of schedules are not identical, the course is updated
        if json_schedules_set != db_schedules_set:
            updated_courses.append({
                "course_code": code,
                "json_schedules": len(json_schedules_set),
                "db_schedules": len(db_schedules_set),
            })
    # --- End Deep Schedule Comparison ---

    # Count total schedules
    json_schedules = sum(len(data.get("schedules", [])) for data in json_data.values())
    db_schedules = sum(len(data.get("schedules", [])) for data in db_data.values())
    
    # Count courses with schedules
    json_courses_with_schedules = sum(1 for data in json_data.values() if data.get("schedules"))
    db_courses_with_schedules = sum(1 for data in db_data.values() if data.get("schedules"))
    
    return {
        "json_courses": len(json_data),
        "db_courses": len(db_data),
        "json_schedules": json_schedules,
        "db_schedules": db_schedules,
        "json_courses_with_schedules": json_courses_with_schedules,
        "db_courses_with_schedules": db_courses_with_schedules,
        "only_in_json": len(only_in_json),
        "only_in_db": len(only_in_db),
        "in_both": len(in_both),
        "updated_courses": updated_courses,
        "new_courses": list(only_in_json),
        "missing_courses": list(only_in_db),
    }


def print_comparison(results: dict):
    """Print comparison results"""
    print("\n" + "="*60)
    print("DATA COMPARISON RESULTS")
    print("="*60)
    
    print(f"JSON Files:")
    print(f"  - Total courses: {results['json_courses']}")
    print(f"  - Total schedules: {results['json_schedules']}")
    print(f"  - Courses with schedules: {results['json_courses_with_schedules']}")
    
    print(f"\nDatabase:")
    print(f"  - Total courses: {results['db_courses']}")
    print(f"  - Total schedules: {results['db_schedules']}")
    print(f"  - Courses with schedules: {results['db_courses_with_schedules']}")
    
    print(f"\nComparison:")
    print(f"  - Courses in both: {results['in_both']}")
    print(f"  - New courses (only in JSON): {results['only_in_json']}")
    print(f"  - Missing courses (only in DB): {results['only_in_db']}")
    print(f"  - Updated courses (schedule mismatch): {len(results['updated_courses'])}")

    if results['new_courses']:
        print(f"\nNew courses to be added:")
        for course in results['new_courses']:
            print(f"  - {course}")
            
    if results['updated_courses']:
        print(f"\nCourses with updated schedules:")
        for course in results['updated_courses']:
            print(f"  - {course['course_code']} (Scraped: {course['json_schedules']} schedules vs. DB: {course['db_schedules']} schedules)")

    if results['missing_courses']:
        print(f"\nMissing courses to be removed:")
        for course in results['missing_courses']:
            print(f"  - {course}")
    
    print("="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare scraped JSON with database data")
    parser.add_argument("--test", action="store_true", help="Run in test mode with only 5 files")
    parser.add_argument("--json-dir", type=str, help="Directory containing JSON files", 
                       default="../data/course_data")
    
    args = parser.parse_args()
    
    # Read JSON data
    json_data = read_json_data(args.json_dir, test_mode=args.test)
    
    # Read database data
    db_data = read_database_data()
    
    # Compare data
    results = compare_data(json_data, db_data)
    
    # Print results
    print_comparison(results) 