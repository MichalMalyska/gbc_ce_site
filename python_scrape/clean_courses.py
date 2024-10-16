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

    with open(DATA_PATH / "courses.txt", "r") as f:
        courses = f.readlines()
    clean_courses = []
    for course in courses:
        if not course.endswith("-program"):
            clean_courses.append(course.strip())
        else:
            print(f"Skipping {course.strip()} because it is a program")
    with open(DATA_PATH / "courses.txt", "w") as f:
        f.write("\n".join(clean_courses))


if __name__ == "__main__":
    clean_courses()
