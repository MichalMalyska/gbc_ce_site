import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional


logger = logging.getLogger(__name__)

DAY_ORDER = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
DAY_INDEX = {day: index for index, day in enumerate(DAY_ORDER)}
DAY_VARIANTS = {
    "m": "Monday",
    "mon": "Monday",
    "monday": "Monday",
    "t": "Tuesday",
    "tu": "Tuesday",
    "tue": "Tuesday",
    "tues": "Tuesday",
    "tuesday": "Tuesday",
    "w": "Wednesday",
    "wed": "Wednesday",
    "wednesday": "Wednesday",
    "th": "Thursday",
    "thu": "Thursday",
    "thur": "Thursday",
    "thurs": "Thursday",
    "thursday": "Thursday",
    "f": "Friday",
    "fri": "Friday",
    "friday": "Friday",
    "sa": "Saturday",
    "sat": "Saturday",
    "saturday": "Saturday",
    "su": "Sunday",
    "sun": "Sunday",
    "sunday": "Sunday",
}
DAY_TOKEN_RE = "|".join(re.escape(token) for token in sorted(DAY_VARIANTS, key=len, reverse=True))
TOKEN_RE = re.compile(
    rf"(?P<day>{DAY_TOKEN_RE})|(?P<connector>,|/|&|\band\b|\bto\b|-|–|—)",
    re.IGNORECASE,
)
WHITESPACE_RE = re.compile(r"\s+")
EMPTY_DAY_RE = re.compile(r"^(?:[-–—/\s]+|n/?a|tba|tbd)?$", re.IGNORECASE)
FLEXIBLE_MARKERS = (
    "full day",
    "self-directed",
    "self directed",
    "self-paced",
    "self paced",
    "flexible",
)
INVALID_REPORT_PATH = Path(__file__).resolve().parents[2] / "data" / "errors" / "invalid_schedules.json"


class DayOfWeekNormalizationError(ValueError):
    """Raised when a weekday string cannot be normalized to the canonical contract."""


def _normalize_text(value: Optional[str]) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\xa0", " ").replace("\u202f", " ").replace("\u2011", "-")
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _is_flexible_day_marker(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in FLEXIBLE_MARKERS)


def _normalize_day_token(token: str) -> str:
    normalized = DAY_VARIANTS.get(token.lower())
    if normalized is None:
        raise DayOfWeekNormalizationError(f"Unrecognized day token: {token}")
    return normalized


def _normalize_connector(token: str) -> str:
    lowered = token.lower()
    if lowered in {",", "/", "&", "and"}:
        return "list"
    if lowered in {"-", "–", "—", "to"}:
        return "range"
    raise DayOfWeekNormalizationError(f"Unrecognized connector: {token}")


def _expand_day_range(start_day: str, end_day: str) -> list[str]:
    start_index = DAY_INDEX[start_day]
    end_index = DAY_INDEX[end_day]
    if start_index > end_index:
        raise DayOfWeekNormalizationError(f"Unsupported wrapped weekday range: {start_day} to {end_day}")
    return list(DAY_ORDER[start_index : end_index + 1])


def sort_unique_days(days: Iterable[str]) -> list[str]:
    unique_days = {day for day in days}
    return [day for day in DAY_ORDER if day in unique_days]


def split_canonical_day_of_week(value: Optional[str]) -> list[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return []
    return [part.strip() for part in normalized.split(",") if part.strip()]


def normalize_day_of_week(value: Optional[str]) -> str:
    normalized_text = _normalize_text(value)
    if not normalized_text or EMPTY_DAY_RE.fullmatch(normalized_text) or _is_flexible_day_marker(normalized_text):
        return ""

    tokens: list[tuple[str, str]] = []
    last_end = 0
    for match in TOKEN_RE.finditer(normalized_text):
        gap = normalized_text[last_end : match.start()]
        if gap.strip():
            raise DayOfWeekNormalizationError(f"Unexpected weekday text: {gap.strip()}")

        if match.group("day") is not None:
            if tokens and tokens[-1][0] == "day":
                tokens.append(("connector", "list"))
            tokens.append(("day", _normalize_day_token(match.group("day"))))
        else:
            if not tokens or tokens[-1][0] == "connector":
                raise DayOfWeekNormalizationError(f"Unexpected connector in weekday string: {normalized_text}")
            tokens.append(("connector", _normalize_connector(match.group("connector") or "")))

        last_end = match.end()

    tail = normalized_text[last_end:]
    if tail.strip():
        raise DayOfWeekNormalizationError(f"Unexpected weekday text: {tail.strip()}")

    if not tokens or tokens[-1][0] == "connector":
        raise DayOfWeekNormalizationError(f"Incomplete weekday string: {normalized_text}")

    normalized_days: list[str] = []
    index = 0
    while index < len(tokens):
        _, day_name = tokens[index]
        next_index = index + 1
        if next_index < len(tokens) and tokens[next_index] == ("connector", "range"):
            if next_index + 1 >= len(tokens) or tokens[next_index + 1][0] != "day":
                raise DayOfWeekNormalizationError(f"Incomplete weekday range: {normalized_text}")
            normalized_days.extend(_expand_day_range(day_name, tokens[next_index + 1][1]))
            index = next_index + 2
        else:
            normalized_days.append(day_name)
            index += 1

        if index < len(tokens):
            if tokens[index][0] != "connector" or tokens[index][1] != "list":
                raise DayOfWeekNormalizationError(f"Malformed weekday sequence: {normalized_text}")
            index += 1
            if index >= len(tokens):
                raise DayOfWeekNormalizationError(f"Trailing weekday connector: {normalized_text}")

    return ", ".join(sort_unique_days(normalized_days))


def normalize_day_filter_tokens(value: Optional[str]) -> list[str]:
    normalized = normalize_day_of_week(value)
    return split_canonical_day_of_week(normalized)


def get_schedule_day_value(schedule: Mapping[str, Any]) -> str:
    return str(schedule.get("day_or_days_of_week") or schedule.get("day_of_week") or "")


def build_invalid_schedule_record(
    *,
    context: str,
    course_code: Optional[str],
    reason_code: str,
    raw_schedule: Mapping[str, Any],
    source_file: Optional[str] = None,
    normalized_schedule: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "context": context,
        "course_code": course_code or "",
        "source_file": source_file,
        "reason_code": reason_code,
        "raw_schedule": dict(raw_schedule),
        "normalized_schedule": dict(normalized_schedule) if normalized_schedule is not None else None,
    }


def save_invalid_schedule_report(invalid_schedules: list[dict[str, Any]]) -> None:
    INVALID_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INVALID_REPORT_PATH, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "invalid_schedules": invalid_schedules,
            },
            handle,
            indent=2,
        )

    logger.info("Saved invalid schedule report to %s", INVALID_REPORT_PATH)


def normalize_schedule_day_fields(
    schedule_items: list[dict[str, Any]],
    *,
    context: str,
    course_code: Optional[str],
    source_file: Optional[str] = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized_schedules: list[dict[str, Any]] = []
    invalid_schedules: list[dict[str, Any]] = []

    for schedule in schedule_items:
        raw_day = get_schedule_day_value(schedule)
        try:
            normalized_day = normalize_day_of_week(raw_day)
        except DayOfWeekNormalizationError as exc:
            logger.warning(
                "Skipping schedule with invalid day_of_week for %s (%s): %s",
                course_code or "UNKNOWN",
                source_file or context,
                exc,
            )
            invalid_schedules.append(
                build_invalid_schedule_record(
                    context=context,
                    course_code=course_code,
                    source_file=source_file,
                    reason_code="invalid_day_of_week",
                    raw_schedule=schedule,
                )
            )
            continue

        normalized_schedule = dict(schedule)
        if "day_or_days_of_week" in normalized_schedule or "day_of_week" not in normalized_schedule:
            normalized_schedule["day_or_days_of_week"] = normalized_day
        if "day_of_week" in normalized_schedule:
            normalized_schedule["day_of_week"] = normalized_day
        normalized_schedules.append(normalized_schedule)

    return normalized_schedules, invalid_schedules


def normalize_course_schedule_payload(
    course: dict[str, Any],
    *,
    context: str,
    source_file: Optional[str] = None,
) -> list[dict[str, Any]]:
    course_code = course.get("course_code")
    schedule_items = course.get("schedules", [])
    if not isinstance(schedule_items, list):
        schedule_items = []

    normalized_schedules, invalid_schedules = normalize_schedule_day_fields(
        schedule_items,
        context=context,
        course_code=str(course_code or ""),
        source_file=source_file,
    )
    course["schedules"] = normalized_schedules

    if "cleaned_response_schedules" in course or normalized_schedules:
        course["cleaned_response_schedules"] = json.dumps({"schedules": normalized_schedules})

    return invalid_schedules
