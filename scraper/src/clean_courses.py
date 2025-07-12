import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).parent.parent.parent / "data"


def clean_courses():
    """Remove program files and invalid course files"""
    all_courses = os.listdir(DATA_PATH / "course_data")
    removed = 0

    for course in all_courses:
        file_path = DATA_PATH / "course_data" / course
        if course.startswith(" -") or "Program" in course or "program" in course:
            os.remove(file_path)
            removed += 1
            logger.info(f"Removed {course}")

    logger.info(f"Removed {removed} invalid course files")


if __name__ == "__main__":
    clean_courses()
