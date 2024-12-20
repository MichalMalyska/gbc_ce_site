from datetime import time
from pathlib import Path

from python_scrape.db.queries import (
    get_evening_courses_by_days_json,
    get_evening_courses_summary_json,
    get_in_person_courses_by_department_json,
)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("department", help="Department code (e.g., HOSF)")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument(
        "--evening-days",
        nargs="+",
        choices=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        help="Only show courses on these days after 5PM",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Only show course codes and links",
    )
    args = parser.parse_args()

    # Default output file if none specified
    if not args.output:
        output_dir = Path(__file__).parent.parent.parent / "data" / "query_results"
        output_dir.mkdir(exist_ok=True)
        suffix = "_evening" if args.evening_days else ""
        suffix += "_summary" if args.summary else ""
        args.output = output_dir / f"{args.department.lower()}{suffix}_courses.json"

    # Run appropriate query
    if args.evening_days:
        if args.summary:
            json_data = get_evening_courses_summary_json(
                department=args.department,
                days=args.evening_days,
                after_time=time(17, 0),  # 5:00 PM
                output_file=args.output.as_posix(),
            )
        else:
            json_data = get_evening_courses_by_days_json(
                department=args.department,
                days=args.evening_days,
                after_time=time(17, 0),  # 5:00 PM
                output_file=args.output.as_posix(),
            )
    else:
        json_data = get_in_person_courses_by_department_json(
            department=args.department,
            output_file=args.output.as_posix(),
        )

    print(f"Found {len(json_data)} courses")
    print(f"Results saved to: {args.output}")
