import importlib
import json
import os
import sys
from datetime import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRAPER_ROOT = REPO_ROOT / "scraper"
if str(SCRAPER_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRAPER_ROOT))


def load_modules(database_url: str):
    os.environ["DATABASE_URL"] = database_url
    for module_name in ["db.load_data", "db.database", "db.queries", "src.filters", "src.schedule_utils"]:
        sys.modules.pop(module_name, None)

    schedule_utils_module = importlib.import_module("src.schedule_utils")
    database_module = importlib.import_module("db.database")
    load_data_module = importlib.import_module("db.load_data")
    queries_module = importlib.import_module("db.queries")
    filters_module = importlib.import_module("src.filters")
    return database_module, load_data_module, queries_module, filters_module, schedule_utils_module


def write_course_json(output_dir: Path, payload: dict) -> None:
    file_name = f"{payload['course_code']} - {payload['course_name']}.json"
    with open(output_dir / file_name, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def read_invalid_schedule_report(report_path: Path) -> dict:
    with open(report_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_load_course_data_syncs_into_empty_database_and_overwrites_existing_rows(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'courses.db'}"
    database_module, load_data_module, _, _, _ = load_modules(database_url)

    json_dir = tmp_path / "course_data"
    json_dir.mkdir()

    first_course = {
        "course_code": "ACCT 1049",
        "course_name": "Hospitality Accounting",
        "course_delivery_type": "Online",
        "prereqs": "",
        "hours": "21",
        "fees": "$185.65",
        "course_description": "Original description",
        "course_link": "https://example.com/acct-1049",
        "schedules": [
            {
                "start_date": "2025-01-13",
                "end_date": "2025-02-24",
                "day_or_days_of_week": "Monday",
                "start_time": "6:00 PM",
                "end_time": "9:00 PM",
            }
        ],
    }
    second_course = {
        "course_code": "BUS 9210",
        "course_name": "Leadership Basics",
        "course_delivery_type": "Online",
        "prereqs": "",
        "hours": "18",
        "fees": "$120.00",
        "course_description": "Second course",
        "course_link": "https://example.com/bus-9210",
        "schedules": [],
    }

    write_course_json(json_dir, first_course)
    write_course_json(json_dir, second_course)

    load_data_module.load_course_data(str(json_dir), reset=True)

    session = database_module.SessionLocal()
    try:
        courses = session.query(database_module.Course).order_by(database_module.Course.course_code).all()
        assert [course.course_code for course in courses] == ["ACCT 1049", "BUS 9210"]

        synced_course = courses[0]
        assert synced_course.course_description == "Original description"
        assert synced_course.last_seen_at is not None
        assert len(synced_course.schedules) == 1
        assert synced_course.schedules[0].start_date.isoformat() == "2025-01-13"
        assert synced_course.schedules[0].start_time == time(18, 0)
    finally:
        session.close()


def test_parse_time_handles_placeholders_and_common_variants(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'time-helpers.db'}"
    _, load_data_module, _, _, _ = load_modules(database_url)

    assert load_data_module.parse_time("") is None
    assert load_data_module.parse_time("—") is None
    assert load_data_module.parse_time("TBA") is None
    assert load_data_module.parse_time("N/A") is None
    assert load_data_module.parse_time("6:15 p.m.") == time(18, 15)
    assert load_data_module.parse_time("9 a.m.") == time(9, 0)

    assert load_data_module.extract_time_component("6:30 – 9:30 PM", side="start") == "6:30 PM"
    assert load_data_module.extract_time_component("6:30 – 9:30 PM", side="end") == "9:30 PM"
    assert load_data_module.extract_time_component("6:30 - 9:30 p.m.", side="start") == "6:30 PM"
    assert load_data_module.extract_time_component("6:30 - 9:30 p.m.", side="end") == "9:30 p.m."


def test_load_course_data_normalizes_placeholder_and_range_times(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'time-normalization.db'}"
    database_module, load_data_module, _, _, _ = load_modules(database_url)

    json_dir = tmp_path / "course_data"
    json_dir.mkdir()

    placeholder_course = {
        "course_code": "COMP 9735",
        "course_name": "AWS SysOps Administration",
        "course_delivery_type": "Online",
        "prereqs": "",
        "hours": "42",
        "fees": "$507.32",
        "course_description": "Self-directed course",
        "course_link": "https://example.com/comp-9735",
        "schedules": [
            {
                "start_date": "2026-03-02",
                "end_date": "2026-06-07",
                "day_or_days_of_week": "",
                "start_time": "—",
                "end_time": "—",
            }
        ],
    }
    range_course = {
        "course_code": "HOST 1145",
        "course_name": "Mixology",
        "course_delivery_type": "On Campus",
        "prereqs": "",
        "hours": "42",
        "fees": "$557.32",
        "course_description": "Teacher-led course",
        "course_link": "https://example.com/host-1145",
        "schedules": [
            {
                "start_date": "2026-05-04",
                "end_date": "2026-08-17",
                "day_or_days_of_week": "Monday",
                "start_time": "6:30 – 9:30 PM",
                "end_time": "6:30 – 9:30 PM",
            }
        ],
    }

    write_course_json(json_dir, placeholder_course)
    write_course_json(json_dir, range_course)

    load_data_module.load_course_data(str(json_dir), reset=True)

    session = database_module.SessionLocal()
    try:
        placeholder = (
            session.query(database_module.Course).filter(database_module.Course.course_code == "COMP 9735").one()
        )
        assert len(placeholder.schedules) == 1
        assert placeholder.schedules[0].start_time is None
        assert placeholder.schedules[0].end_time is None

        ranged = session.query(database_module.Course).filter(database_module.Course.course_code == "HOST 1145").one()
        assert len(ranged.schedules) == 1
        assert ranged.schedules[0].start_time == time(18, 30)
        assert ranged.schedules[0].end_time == time(21, 30)
    finally:
        session.close()


def test_normalize_day_of_week_handles_variants_ranges_and_flexible_markers(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'day-normalization.db'}"
    _, _, _, _, schedule_utils_module = load_modules(database_url)

    normalize_day_of_week = schedule_utils_module.normalize_day_of_week

    assert normalize_day_of_week("Tu") == "Tuesday"
    assert normalize_day_of_week("Tue") == "Tuesday"
    assert normalize_day_of_week("Th") == "Thursday"
    assert normalize_day_of_week("Mon, Wed") == "Monday, Wednesday"
    assert normalize_day_of_week("Tue / Thu") == "Tuesday, Thursday"
    assert normalize_day_of_week("Tues and Thurs") == "Tuesday, Thursday"
    assert normalize_day_of_week("Monday - Friday") == "Monday, Tuesday, Wednesday, Thursday, Friday"
    assert normalize_day_of_week("Friday – Sunday") == "Friday, Saturday, Sunday"
    assert normalize_day_of_week("Saturday and Sunday") == "Saturday, Sunday"
    assert normalize_day_of_week("Self-directed") == ""
    assert normalize_day_of_week("Full day names") == ""

    with pytest.raises(schedule_utils_module.DayOfWeekNormalizationError):
        normalize_day_of_week("Funday")


def test_load_course_data_normalizes_weekdays_and_logs_invalid_schedules(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'weekday-validation.db'}"
    database_module, load_data_module, _, _, schedule_utils_module = load_modules(database_url)
    report_path = tmp_path / "invalid_schedules.json"
    monkeypatch.setattr(schedule_utils_module, "INVALID_REPORT_PATH", report_path)

    json_dir = tmp_path / "course_data"
    json_dir.mkdir()

    course_payload = {
        "course_code": "ELCL 9061",
        "course_name": "Allen-Bradley PLC 1",
        "course_delivery_type": "Online",
        "prereqs": "",
        "hours": "42",
        "fees": "$557.32",
        "course_description": "Teacher-led course",
        "course_link": "https://example.com/elcl-9061",
        "schedules": [
            {
                "start_date": "2026-05-05",
                "end_date": "2026-08-04",
                "day_or_days_of_week": "Tu",
                "start_time": "6:15 p.m.",
                "end_time": "9:15 p.m.",
            },
            {
                "start_date": "2026-05-26",
                "end_date": "2026-06-18",
                "day_or_days_of_week": "Tues and Thurs",
                "start_time": "6:30 – 9:30 p.m.",
                "end_time": "",
            },
            {
                "start_date": "2026-05-26",
                "end_date": "2026-06-18",
                "day_or_days_of_week": "Tue / Thu",
                "start_time": "6:30 PM",
                "end_time": "9:30 PM",
            },
            {
                "start_date": "2026-03-16",
                "end_date": "2026-03-20",
                "day_or_days_of_week": "Monday - Friday",
                "start_time": "9:30 a.m.",
                "end_time": "4 p.m.",
            },
            {
                "start_date": "2026-05-23",
                "end_date": "2026-06-13",
                "day_or_days_of_week": "Sa",
                "start_time": "9:30 a.m.",
                "end_time": "3 p.m.",
            },
            {
                "start_date": "2026-03-02",
                "end_date": "2026-06-07",
                "day_or_days_of_week": "Self-directed",
                "start_time": "—",
                "end_time": "—",
            },
            {
                "start_date": "2026-05-12",
                "end_date": "2026-08-18",
                "day_or_days_of_week": "Funday",
                "start_time": "6:15 PM",
                "end_time": "9:15 PM",
            },
            {
                "start_date": "not-a-date",
                "end_date": "2026-08-18",
                "day_or_days_of_week": "Tuesday",
                "start_time": "6:15 PM",
                "end_time": "9:15 PM",
            },
            {
                "start_date": "2026-08-18",
                "end_date": "2026-05-12",
                "day_or_days_of_week": "Tuesday",
                "start_time": "6:15 PM",
                "end_time": "9:15 PM",
            },
            {
                "start_date": "2026-05-12",
                "end_date": "2026-08-18",
                "day_or_days_of_week": "Thursday",
                "start_time": "6:15 PM",
                "end_time": "",
            },
            {
                "start_date": "2026-05-12",
                "end_date": "2026-08-18",
                "day_or_days_of_week": "Thursday",
                "start_time": "9:15 PM",
                "end_time": "6:15 PM",
            },
        ],
    }

    write_course_json(json_dir, course_payload)
    load_data_module.load_course_data(str(json_dir), reset=True)

    session = database_module.SessionLocal()
    try:
        course = session.query(database_module.Course).filter(database_module.Course.course_code == "ELCL 9061").one()
        stored_days = sorted(schedule.day_of_week for schedule in course.schedules)
        assert stored_days == [
            "",
            "Monday, Tuesday, Wednesday, Thursday, Friday",
            "Saturday",
            "Tuesday",
            "Tuesday, Thursday",
        ]

        schedules_by_day = {schedule.day_of_week: schedule for schedule in course.schedules}
        assert schedules_by_day["Tuesday"].start_time == time(18, 15)
        assert schedules_by_day["Tuesday, Thursday"].start_time == time(18, 30)
        assert schedules_by_day["Tuesday, Thursday"].end_time == time(21, 30)
        assert schedules_by_day[""].start_time is None
        assert schedules_by_day[""].end_time is None
    finally:
        session.close()

    report = read_invalid_schedule_report(report_path)
    reason_codes = [item["reason_code"] for item in report["invalid_schedules"]]
    assert sorted(reason_codes) == [
        "date_range_reversed",
        "incomplete_time_pair",
        "invalid_date",
        "invalid_day_of_week",
        "time_range_reversed",
    ]
    assert {item["source_file"] for item in report["invalid_schedules"]} == {"ELCL 9061 - Allen-Bradley PLC 1.json"}


def test_cleanup_path_rewrites_existing_json_before_db_sync(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'cleanup-path.db'}"
    database_module, load_data_module, _, _, schedule_utils_module = load_modules(database_url)
    monkeypatch.setattr(schedule_utils_module, "INVALID_REPORT_PATH", tmp_path / "cleanup-invalid-schedules.json")

    json_dir = tmp_path / "course_data"
    json_dir.mkdir()
    payload = {
        "course_code": "COMP 1234",
        "course_name": "Cleanup Test",
        "course_delivery_type": "Online",
        "prereqs": "",
        "hours": "21",
        "fees": "$185.65",
        "course_description": "Normalization pass",
        "course_link": "https://example.com/comp-1234",
        "schedules": [
            {
                "start_date": "2026-05-12",
                "end_date": "2026-07-21",
                "day_or_days_of_week": "Mon, Wed",
                "start_time": "6:15 PM",
                "end_time": "9:15 PM",
            },
            {
                "start_date": "2026-03-02",
                "end_date": "2026-06-07",
                "day_or_days_of_week": "Full day",
                "start_time": "—",
                "end_time": "—",
            },
        ],
        "cleaned_response_schedules": json.dumps(
            {
                "schedules": [
                    {
                        "start_date": "2026-05-12",
                        "end_date": "2026-07-21",
                        "day_or_days_of_week": "Mon, Wed",
                        "start_time": "6:15 PM",
                        "end_time": "9:15 PM",
                    },
                    {
                        "start_date": "2026-03-02",
                        "end_date": "2026-06-07",
                        "day_or_days_of_week": "Full day",
                        "start_time": "—",
                        "end_time": "—",
                    },
                ]
            }
        ),
    }

    write_course_json(json_dir, payload)
    file_path = json_dir / "COMP 1234 - Cleanup Test.json"

    loaded_payload = json.loads(file_path.read_text(encoding="utf-8"))
    invalid_schedules = schedule_utils_module.normalize_course_schedule_payload(
        loaded_payload,
        context="scrape_json_load",
        source_file=file_path.name,
    )
    assert invalid_schedules == []

    file_path.write_text(json.dumps(loaded_payload), encoding="utf-8")
    rewritten_payload = json.loads(file_path.read_text(encoding="utf-8"))
    assert rewritten_payload["schedules"][0]["day_or_days_of_week"] == "Monday, Wednesday"
    assert rewritten_payload["schedules"][1]["day_or_days_of_week"] == ""
    assert json.loads(rewritten_payload["cleaned_response_schedules"]) == {"schedules": rewritten_payload["schedules"]}

    load_data_module.load_course_data(str(json_dir), reset=True)

    session = database_module.SessionLocal()
    try:
        stored_days = [
            schedule.day_of_week
            for schedule in (
                session.query(database_module.Schedule)
                .join(database_module.Course)
                .filter(database_module.Course.course_code == "COMP 1234")
                .order_by(database_module.Schedule.id)
            )
        ]
        assert stored_days == ["Monday, Wednesday", ""]
    finally:
        session.close()


def test_queries_and_filters_accept_abbreviated_day_inputs(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'query-filters.db'}"
    _, load_data_module, queries_module, filters_module, schedule_utils_module = load_modules(database_url)
    monkeypatch.setattr(schedule_utils_module, "INVALID_REPORT_PATH", tmp_path / "query-invalid-schedules.json")

    json_dir = tmp_path / "course_data"
    json_dir.mkdir()

    tuesday_course = {
        "course_code": "ELCL 1001",
        "course_name": "Tuesday Course",
        "course_delivery_type": "On Campus",
        "prereqs": "",
        "hours": "21",
        "fees": "$185.65",
        "course_description": "Tuesday schedule",
        "course_link": "https://example.com/elcl-1001",
        "schedules": [
            {
                "start_date": "2026-05-12",
                "end_date": "2026-07-21",
                "day_or_days_of_week": "Tu",
                "start_time": "6:15 PM",
                "end_time": "9:15 PM",
            }
        ],
    }
    monday_course = {
        "course_code": "ELCL 1002",
        "course_name": "Monday Course",
        "course_delivery_type": "On Campus",
        "prereqs": "",
        "hours": "21",
        "fees": "$185.65",
        "course_description": "Monday schedule",
        "course_link": "https://example.com/elcl-1002",
        "schedules": [
            {
                "start_date": "2026-05-05",
                "end_date": "2026-07-14",
                "day_or_days_of_week": "Monday",
                "start_time": "6:15 PM",
                "end_time": "9:15 PM",
            }
        ],
    }

    write_course_json(json_dir, tuesday_course)
    write_course_json(json_dir, monday_course)
    load_data_module.load_course_data(str(json_dir), reset=True)

    tu_results = sorted(course.course_code for course in queries_module.get_courses_by_filters(day_of_week="Tu"))
    tue_results = sorted(course.course_code for course in queries_module.get_courses_by_filters(day_of_week="Tuesday"))
    assert tu_results == tue_results == ["ELCL 1001"]

    summary = json.loads(queries_module.get_evening_courses_summary_json("ELCL", ["Th", "Tu"], time(18, 0)))
    assert [item["course_code"] for item in summary] == ["ELCL 1001"]

    courses_payload = [
        {"course_code": "ELCL 1001", "schedules": [{"day_or_days_of_week": "Tu & Th"}]},
        {"course_code": "ELCL 1002", "schedules": [{"day_or_days_of_week": "Monday"}]},
    ]
    assert [course["course_code"] for course in filters_module.filter_courses_by_day(courses_payload, "Tuesday")] == [
        "ELCL 1001"
    ]
    assert [course["course_code"] for course in filters_module.filter_courses_by_day(courses_payload, "Th")] == [
        "ELCL 1001"
    ]
