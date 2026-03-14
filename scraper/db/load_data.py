import json
import logging
import re
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Optional

from src.schedule_utils import (
    build_invalid_schedule_record,
    get_schedule_day_value,
    normalize_schedule_day_fields,
    save_invalid_schedule_report,
)

from .database import Course, Schedule, SessionLocal, drop_and_recreate_tables, init_db

log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "db_load.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

TIME_PLACEHOLDERS = {"", "-", "—", "–", "n/a", "na", "tba", "tbd"}
TIME_RANGE_SEPARATOR_RE = re.compile(r"\s*[–—-]\s*")
MERIDIEM_SUFFIX_RE = re.compile(r"\b([ap])\.?\s*m\.?\b", re.IGNORECASE)


def normalize_time_string(time_str: str) -> str:
    """Normalize a single time string without applying timezone conversion."""
    normalized = time_str.strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.replace("a.m.", "AM").replace("p.m.", "PM")
    normalized = normalized.replace("a.m", "AM").replace("p.m", "PM")
    normalized = re.sub(r"\b(am|pm)\b", lambda match: match.group(1).upper(), normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\b([ap])\s*m\b", lambda match: f"{match.group(1).upper()}M", normalized, flags=re.IGNORECASE)

    meridiem_match = MERIDIEM_SUFFIX_RE.search(normalized)
    if meridiem_match:
        suffix = f"{meridiem_match.group(1).upper()}M"
        normalized = MERIDIEM_SUFFIX_RE.sub(suffix, normalized)

    if re.fullmatch(r"\d{1,2}\s*(AM|PM)", normalized):
        hour, suffix = normalized[:-2].strip(), normalized[-2:]
        normalized = f"{hour}:00 {suffix}"
    elif re.fullmatch(r"\d{1,2}:\d{2}\s*(AM|PM)", normalized):
        normalized = re.sub(r"\s*(AM|PM)$", r" \1", normalized)

    return normalized


def extract_time_component(time_str: str, side: str) -> str:
    """Extract a start or end time from a range-like string."""
    parts = [part.strip() for part in TIME_RANGE_SEPARATOR_RE.split(time_str) if part.strip()]
    if len(parts) != 2:
        return time_str

    start_part, end_part = parts
    start_meridiem = MERIDIEM_SUFFIX_RE.search(start_part)
    end_meridiem = MERIDIEM_SUFFIX_RE.search(end_part)
    if start_meridiem is None and end_meridiem is not None:
        start_part = f"{start_part} {end_meridiem.group(1).upper()}M"

    return start_part if side == "start" else end_part


def is_time_placeholder(time_str: str) -> bool:
    """Return True when a time string intentionally represents no time."""
    return not time_str or time_str.strip().lower() in TIME_PLACEHOLDERS


def resolve_time_components(raw_start_time: str, raw_end_time: str) -> tuple[str, str]:
    """Split one-sided time ranges into start/end components when possible."""
    start_value = raw_start_time.strip()
    end_value = raw_end_time.strip()

    if TIME_RANGE_SEPARATOR_RE.search(start_value) and is_time_placeholder(end_value):
        return extract_time_component(start_value, side="start"), extract_time_component(start_value, side="end")

    if TIME_RANGE_SEPARATOR_RE.search(end_value) and is_time_placeholder(start_value):
        return extract_time_component(end_value, side="start"), extract_time_component(end_value, side="end")

    normalized_start = extract_time_component(start_value, side="start") if start_value else start_value
    normalized_end = extract_time_component(end_value, side="end") if end_value else end_value
    return normalized_start, normalized_end


def parse_time(time_str: str) -> Optional[time]:
    """Parse local Toronto wall-clock times without applying timezone conversion."""
    if not time_str:
        return None

    if time_str.strip().lower() in TIME_PLACEHOLDERS:
        return None

    time_str = normalize_time_string(time_str)

    formats = [
        "%I:%M %p",
        "%I:%M%p",
        "%H:%M",
        "%I:%M",
        "%I %p",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue

    logger.error(f"Could not parse time string: {time_str}")
    return None


def parse_date(date_str: str) -> Optional[date]:
    """Parse dates as local calendar dates without timezone conversion."""
    if not date_str:
        return None

    date_str = date_str.strip()
    formats = [
        "%Y-%m-%d",
        "%d%b%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    logger.error(f"Could not parse date string: {date_str}")
    return None


def split_course_code(course_code: str) -> tuple[str, str]:
    """Split a course code into its prefix and number parts."""
    try:
        parts = course_code.split(" ", 1)
        if len(parts) != 2:
            logger.warning(f"Invalid course code format: {course_code}")
            return course_code, ""

        prefix, number = parts
        if not (3 <= len(prefix) <= 4 and prefix.isalpha()):
            logger.warning(f"Invalid course prefix: {prefix}")
            return course_code, ""

        if not number.isdigit():
            logger.warning(f"Invalid course number: {number}")
            return course_code, ""

        return prefix, number
    except Exception as exc:
        logger.error(f"Error splitting course code {course_code}: {exc}")
        return course_code, ""


def save_failed_courses(failed_courses: list[dict[str, Any]]) -> None:
    """Save details of failed course processing to a file."""
    output_dir = Path(__file__).parent.parent.parent / "data" / "errors"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "failed_courses.json"

    try:
        with open(output_file, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "failed_courses": failed_courses,
                },
                handle,
                indent=2,
            )
        logger.info(f"Saved failed courses report to {output_file}")
    except Exception as exc:
        logger.error(f"Error saving failed courses report: {exc}")


def iter_json_files(json_dir: str, test_mode: bool = False) -> list[Path]:
    """Load JSON file paths from disk."""
    json_files = sorted(Path(json_dir).glob("*.json"))
    logger.info(f"Found {len(json_files)} JSON files to process")

    if test_mode:
        json_files = json_files[:5]
        logger.info(f"TEST MODE: Processing only {len(json_files)} files")
        for json_file in json_files:
            logger.info(f"  - {json_file.name}")

    return json_files


def build_schedules(
    schedule_items: list[dict[str, Any]],
    *,
    course_code: str,
    source_file: Optional[str] = None,
    invalid_schedules: Optional[list[dict[str, Any]]] = None,
) -> list[Schedule]:
    """Build schedule ORM objects, collapsing exact duplicates from a single scrape payload."""
    schedules: list[Schedule] = []
    seen_schedule_keys: set[tuple[Any, ...]] = set()
    invalid_schedules = invalid_schedules if invalid_schedules is not None else []
    normalized_schedule_items, invalid_day_records = normalize_schedule_day_fields(
        schedule_items,
        context="db_load",
        course_code=course_code,
        source_file=source_file,
    )
    invalid_schedules.extend(invalid_day_records)

    for schedule_data in normalized_schedule_items:
        day_of_week = get_schedule_day_value(schedule_data)
        start_date = parse_date(schedule_data.get("start_date", ""))
        end_date = parse_date(schedule_data.get("end_date", ""))
        raw_start_time = schedule_data.get("start_time", "") or ""
        raw_end_time = schedule_data.get("end_time", "") or ""
        normalized_start_time, normalized_end_time = resolve_time_components(raw_start_time, raw_end_time)
        start_time = parse_time(normalized_start_time)
        end_time = parse_time(normalized_end_time)

        if not start_date or not end_date:
            invalid_schedules.append(
                build_invalid_schedule_record(
                    context="db_load",
                    course_code=course_code,
                    source_file=source_file,
                    reason_code="invalid_date",
                    raw_schedule=schedule_data,
                    normalized_schedule={"day_of_week": day_of_week},
                )
            )
            logger.warning("Skipping schedule with invalid date(s) for %s (%s)", course_code, source_file or "db_load")
            continue

        if start_date > end_date:
            invalid_schedules.append(
                build_invalid_schedule_record(
                    context="db_load",
                    course_code=course_code,
                    source_file=source_file,
                    reason_code="date_range_reversed",
                    raw_schedule=schedule_data,
                    normalized_schedule={
                        "day_of_week": day_of_week,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                )
            )
            logger.warning(
                "Skipping schedule with reversed dates for %s (%s): %s > %s",
                course_code,
                source_file or "db_load",
                start_date,
                end_date,
            )
            continue

        invalid_time_inputs = (
            (normalized_start_time and not is_time_placeholder(normalized_start_time) and start_time is None)
            or (normalized_end_time and not is_time_placeholder(normalized_end_time) and end_time is None)
        )
        if invalid_time_inputs:
            invalid_schedules.append(
                build_invalid_schedule_record(
                    context="db_load",
                    course_code=course_code,
                    source_file=source_file,
                    reason_code="invalid_time",
                    raw_schedule=schedule_data,
                    normalized_schedule={
                        "day_of_week": day_of_week,
                        "start_time": normalized_start_time,
                        "end_time": normalized_end_time,
                    },
                )
            )
            logger.warning("Skipping schedule with invalid time(s) for %s (%s)", course_code, source_file or "db_load")
            continue

        if (start_time is None) != (end_time is None):
            invalid_schedules.append(
                build_invalid_schedule_record(
                    context="db_load",
                    course_code=course_code,
                    source_file=source_file,
                    reason_code="incomplete_time_pair",
                    raw_schedule=schedule_data,
                    normalized_schedule={
                        "day_of_week": day_of_week,
                        "start_time": normalized_start_time,
                        "end_time": normalized_end_time,
                    },
                )
            )
            logger.warning(
                "Skipping schedule with incomplete time pair for %s (%s)",
                course_code,
                source_file or "db_load",
            )
            continue

        if start_time is not None and end_time is not None and start_time >= end_time:
            invalid_schedules.append(
                build_invalid_schedule_record(
                    context="db_load",
                    course_code=course_code,
                    source_file=source_file,
                    reason_code="time_range_reversed",
                    raw_schedule=schedule_data,
                    normalized_schedule={
                        "day_of_week": day_of_week,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                    },
                )
            )
            logger.warning(
                "Skipping schedule with non-increasing time range for %s (%s)",
                course_code,
                source_file or "db_load",
            )
            continue

        schedule_key = (start_date, end_date, day_of_week, start_time, end_time)
        if schedule_key in seen_schedule_keys:
            continue
        seen_schedule_keys.add(schedule_key)

        schedules.append(
            Schedule(
                start_date=start_date,
                end_date=end_date,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
            )
        )

    return schedules


def sync_course(
    db,
    data: dict[str, Any],
    *,
    source_file: Optional[str] = None,
    invalid_schedules: Optional[list[dict[str, Any]]] = None,
) -> tuple[str, int]:
    """Insert or overwrite a course and replace its schedules by course_code."""
    course_code = data.get("course_code", "")
    course_prefix, course_number = split_course_code(course_code)
    if not course_code or not course_number:
        raise ValueError("Invalid course code format")

    now = datetime.now(timezone.utc)
    existing_course = db.query(Course).filter(Course.course_code == course_code).one_or_none()
    schedule_items = data.get("schedules", []) if isinstance(data.get("schedules"), list) else []
    schedules = build_schedules(
        schedule_items,
        course_code=course_code,
        source_file=source_file,
        invalid_schedules=invalid_schedules,
    )

    if existing_course is None:
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
            last_seen_at=now,
        )
        course.schedules.extend(schedules)
        db.add(course)
        return "inserted", len(schedules)

    existing_course.course_prefix = course_prefix
    existing_course.course_number = course_number
    existing_course.course_name = data["course_name"]
    existing_course.course_delivery_type = data.get("course_delivery_type")
    existing_course.prereqs = data.get("prereqs")
    existing_course.hours = data.get("hours")
    existing_course.fees = data.get("fees")
    existing_course.course_description = data.get("course_description")
    existing_course.course_link = data.get("course_link")
    existing_course.last_seen_at = now
    existing_course.schedules.clear()
    existing_course.schedules.extend(schedules)
    return "updated", len(schedules)


def load_course_data(json_dir: str, test_mode: bool = False, reset: bool = False) -> None:
    """Load course data from JSON files into the database using course_code keyed sync."""
    failed_courses: list[dict[str, Any]] = []
    invalid_schedules: list[dict[str, Any]] = []
    db = SessionLocal()

    try:
        if reset:
            drop_and_recreate_tables()
            logger.warning("Dropped and recreated database tables")

        init_db()
        logger.info("Initialized database tables")

        json_files = iter_json_files(json_dir=json_dir, test_mode=test_mode)
        inserted_courses = 0
        updated_courses = 0
        schedules_written = 0
        errors = 0

        for index, json_file in enumerate(json_files, start=1):
            data: dict[str, Any] = {}
            try:
                with open(json_file, "r", encoding="utf-8") as handle:
                    data = json.load(handle)

                action, schedule_count = sync_course(
                    db,
                    data,
                    source_file=json_file.name,
                    invalid_schedules=invalid_schedules,
                )
                db.commit()
                schedules_written += schedule_count
                if action == "inserted":
                    inserted_courses += 1
                else:
                    updated_courses += 1

                if index % (5 if test_mode else 100) == 0:
                    logger.info(
                        "Progress: %s files processed, %s inserted, %s updated, %s schedules, %s errors",
                        index,
                        inserted_courses,
                        updated_courses,
                        schedules_written,
                        errors,
                    )

            except Exception as exc:
                failed_courses.append(
                    {
                        "file": json_file.name,
                        "course_code": data.get("course_code", "Unknown"),
                        "reason": str(exc),
                        "has_sections": bool(data.get("course_sections")),
                        "has_schedules": bool(data.get("schedules")),
                    }
                )
                logger.error(f"Error processing {json_file.name}: {exc}", exc_info=True)
                db.rollback()
                errors += 1
                continue

        if failed_courses:
            save_failed_courses(failed_courses)
        save_invalid_schedule_report(invalid_schedules)

        logger.info(
            "\nSummary:\n"
            "- Inserted %s courses\n"
            "- Updated %s courses\n"
            "- Wrote %s schedules\n"
            "- Skipped %s invalid schedules\n"
            "- Encountered %s errors (%s courses failed)\n"
            "See %s for details",
            inserted_courses,
            updated_courses,
            schedules_written,
            len(invalid_schedules),
            errors,
            len(failed_courses),
            log_file,
        )
    except Exception as exc:
        logger.error(f"Error loading data: {exc}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Sync course data from JSON files into the database using course_code as the identity key. "
            "Existing courses are overwritten in place and their schedules are replaced."
        )
    )
    parser.add_argument(
        "--json-dir",
        type=str,
        help="Directory containing JSON files.",
        default=str(Path(__file__).parent.parent.parent / "data" / "course_data"),
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode, processing only a few files.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate tables before syncing. Use this only for clean rebuilds.",
    )
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("Starting data sync script")
    logger.info(f"Loading from: {args.json_dir}")
    if args.test:
        logger.info("RUNNING IN TEST MODE")
    if args.reset:
        logger.warning("RUNNING WITH --reset; database tables will be dropped and recreated")
    logger.info("=" * 50)

    load_course_data(json_dir=args.json_dir, test_mode=args.test, reset=args.reset)

    logger.info("Data sync process finished.")
