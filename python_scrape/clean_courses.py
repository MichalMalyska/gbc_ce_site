import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).parent.parent / "data"


def clean_courses():
    all_courses = os.listdir(DATA_PATH / "course_data")
    for course in all_courses:
        if course.startswith(" -"):
            os.remove(DATA_PATH / "course_data" / course)
