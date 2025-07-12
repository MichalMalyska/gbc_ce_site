import json
import logging
from datetime import datetime, time
from pathlib import Path
from typing import Optional

from .database import Course, Schedule, SessionLocal, drop_and_recreate_tables, init_db

# Configure logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "db_load.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(),  # Also print to console
    ],
)
logger = logging.getLogger(__name__)


def parse_time(time_str: str) -> Optional[time]:
    """Convert time string to time object, handling various formats"""
    if not time_str:
        logger.warning("Empty time string")
        return None

    # Clean up the input
    time_str = time_str.strip().lower()
    time_str = time_str.replace("p.m.", "PM").replace("a.m.", "AM")

    # Try different formats
    formats = [
        "%I:%M %p",  # 9:00 PM
        "%I:%M%p",  # 9:00PM
        "%H:%M",  # 21:00
    ]

    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue

    logger.error(f"Could not parse time string: {time_str}")
    return None


def parse_date(date_str: str) -> Optional[datetime]:
    """Convert date string to datetime object, handling various formats"""
    if not date_str:
        logger.warning("Empty date string")
        return None

    # Clean up the input
    date_str = date_str.strip()

    # Try different formats
    formats = [
        "%Y-%m-%d",  # 2024-01-20
        "%d%b%Y",  # 20Jan2024
        "%B %d, %Y",  # January 20, 2024
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    logger.error(f"Could not parse date string: {date_str}")
    return None


def split_course_code(course_code: str) -> tuple[str, str]:
    """Split course code into prefix and number"""
    try:
        # Split on first space
        parts = course_code.split(" ", 1)
        if len(parts) != 2:
            logger.warning(f"Invalid course code format: {course_code}")
            return course_code, ""

        prefix, number = parts
        # Validate prefix is 3-4 characters
        if not (3 <= len(prefix) <= 4 and prefix.isalpha()):
            logger.warning(f"Invalid course prefix: {prefix}")
            return course_code, ""

        # Validate number is numeric
        if not number.isdigit():
            logger.warning(f"Invalid course number: {number}")
            return course_code, ""

        return prefix, number
    except Exception as e:
        logger.error(f"Error splitting course code {course_code}: {e}")
        return course_code, ""


def save_failed_courses(failed_courses: list[dict]) -> None:
    """Save details of failed course processing to a file"""
    output_dir = Path(__file__).parent.parent.parent / "data" / "errors"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "failed_courses.json"

    try:
        with open(output_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "failed_courses": failed_courses,
                },
                f,
                indent=2,
            )
        logger.info(f"Saved failed courses report to {output_file}")
    except Exception as e:
        logger.error(f"Error saving failed courses report: {e}")


def load_course_data(json_dir: str, test_mode: bool = False):
    """
    Load course data from JSON files into database
    """
    db = SessionLocal()
    failed_courses = []

    try:
        # Drop and recreate tables
        drop_and_recreate_tables()
        logger.info("Dropped and recreated database tables")

        # Initialize database tables
        init_db()
        logger.info("Initialized database tables")

        # Get all JSON files in the directory
        json_files = list(Path(json_dir).glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files to process")

        if test_mode:
            json_files = json_files[:5]
            logger.info(f"TEST MODE: Processing only {len(json_files)} files:")
            for f in json_files:
                logger.info(f"  - {f.name}")

        courses_added = 0
        schedules_added = 0
        errors = 0

        # Create a set to track course codes that have been added in the current session
        added_course_codes = set()

        for json_file in json_files:
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)

                course_code = data.get("course_code", "")
                course_prefix, course_number = split_course_code(course_code)

                # Track failures with reasons
                if not course_code or not course_number:
                    failed_courses.append(
                        {
                            "file": json_file.name,
                            "course_code": course_code,
                            "reason": "Invalid course code format",
                            "has_sections": bool(data.get("course_sections")),
                            "has_schedules": bool(data.get("schedules")),
                        }
                    )
                    logger.warning(f"Skipping {json_file.name} - invalid course code")
                    errors += 1
                    continue

                # Check for duplicates within the batch
                if course_code in added_course_codes:
                    logger.warning(
                        f"Skipping duplicate course in batch: {course_code}"
                    )
                    continue

                # Create course
                course = Course(
                    course_code=course_code,
                    course_prefix=course_prefix,
                    course_number=course_number,
                    course_name=data["course_name"],
                    course_delivery_type=data.get("course_delivery_type"),
                    prereqs=data.get("prereqs"),
                    hours=data.get("hours"),
                    fees=data.get("fees"),
                    course_description=data.get("course_description"),
                    course_link=data.get("course_link"),
                )

                # Add schedules if present
                if "schedules" in data and isinstance(data["schedules"], list):
                    for schedule_data in data["schedules"]:
                        start_date = parse_date(schedule_data.get("start_date", ""))
                        end_date = parse_date(schedule_data.get("end_date", ""))
                        start_time = parse_time(schedule_data.get("start_time", ""))
                        end_time = parse_time(schedule_data.get("end_time", ""))
                        day_of_week = schedule_data.get("day_or_days_of_week", "")

                        if start_date and end_date:  # Only require dates
                            schedule = Schedule(
                                start_date=start_date,
                                end_date=end_date,
                                day_of_week=day_of_week,
                                start_time=start_time,
                                end_time=end_time,
                            )
                            course.schedules.append(schedule)
                            schedules_added += 1

                db.add(course)
                added_course_codes.add(course.course_code)
                courses_added += 1

                # Commit every 100 courses (or every course in test mode)
                if courses_added % (5 if test_mode else 100) == 0:
                    db.commit()
                    logger.info(f"Progress: {courses_added} courses, {schedules_added} schedules ({errors} errors)")

            except Exception as e:
                failed_courses.append(
                    {
                        "file": json_file.name,
                        "course_code": data.get("course_code", "Unknown"),
                        "reason": str(e),
                        "has_sections": bool(data.get("course_sections")),
                        "has_schedules": bool(data.get("schedules")),
                    }
                )
                logger.error(f"Error processing {json_file.name}: {e}", exc_info=True)
                errors += 1
                continue

        # Final commit
        db.commit()

        # Save failed courses report
        if failed_courses:
            save_failed_courses(failed_courses)

        logger.info(
            f"\nSummary:\n"
            f"- Added {courses_added} courses\n"
            f"- Added {schedules_added} schedules\n"
            f"- Encountered {errors} errors ({len(failed_courses)} courses failed)\n"
            f"See {log_file} for details"
        )

    except Exception as e:
        logger.error(f"Error loading data: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Load course data from JSON files into the database. "
        "WARNING: This script will drop and recreate existing tables."
    )
    parser.add_argument(
        "--json-dir",
        type=str,
        help="Directory containing JSON files.",
        default=str(Path(__file__).parent.parent.parent / "data" / "json_all"),
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode, processing only a few files.",
    )
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("Starting data loading script")
    logger.warning("This script will drop and recreate the database tables.")
    logger.info(f"Loading from: {args.json_dir}")
    if args.test:
        logger.info("RUNNING IN TEST MODE")
    logger.info("=" * 50)

    load_course_data(json_dir=args.json_dir, test_mode=args.test)

    logger.info("Data loading process finished.")
