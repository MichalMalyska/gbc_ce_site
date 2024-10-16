import json
import logging
import os
import time
from ast import literal_eval
from pathlib import Path
from typing import Any, Optional

import cohere
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from python_scrape.cohere_extract_dates import clean_response, extract_dates
from python_scrape.constants import MAIN_PAGE_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=Path(__file__).parent / "logs" / "scrape.log",
)
logger = logging.getLogger()

DATA_PATH = Path(__file__).parent.parent / "data"


def extract_programs_from_main_page(main_site_link: str) -> list[str]:
    """
    A course / program link will look like:

    <a href="/courses-and-programs/arts-and-design" data-drupal-link-system-path="node/3941">Arts and Design</a>

    extracts the href part, and adds the main url to it.

    Args:
        html_content str: The html content of the main page

    Returns:
        list[str]: A list of programs
    """
    try:
        response = requests.get(main_site_link)
        soup = BeautifulSoup(response.text, "html.parser")
        programs = []
        for link in tqdm(soup.find_all("a", href=True), desc="Extracting programs from main page"):
            href = link["href"]
            if href.startswith("/courses-and-programs/"):
                programs.append(href)
        return programs
    except Exception as e:
        logger.error(f"Failed to extract programs from {main_site_link}: {e}")
        return []


def check_programs_validity(programs: list[str]) -> tuple[list[str], list[requests.Response]]:
    """
    Check the validity of programs
    """
    # test that all the programs are valid:
    # Remove the "courses-and-programs" part of the link
    programs = [program.replace("courses-and-programs/", "") for program in programs]
    responses = []
    for program in tqdm(programs, desc="Checking programs validity"):
        link = f"{MAIN_PAGE_URL}{program}"
        try:
            response = requests.get(link)
            if response.status_code != 200:
                logger.warning(f"Invalid program: {link}")
                programs.remove(program)
            else:
                responses.append(response)
        except Exception as e:
            logger.error(f"Error checking program {link}: {e}")
    return programs, responses


def separate_subjects_and_programs(
    responses: list[requests.Response], programs: list[str]
) -> tuple[list[str], list[str]]:
    clean_subjects = []
    clean_programs = []
    for response, program in zip(responses, programs):
        program_name = program.split("/")[-1]
        if "subject" in program:
            clean_subjects.append(program)
            with open(
                DATA_PATH / "subject_htmls" / f"{program_name}.html",
                "w",
            ) as f:
                f.write(response.text)
        elif not program.endswith("-programs"):
            clean_programs.append(program)
            with open(
                DATA_PATH / "program_htmls" / f"{program_name}.html",
                "w",
            ) as f:
                f.write(response.text)
        else:
            logger.warning(f"Skipping program: {program}")
    return clean_subjects, clean_programs


def write_programs_and_subjects_to_files(clean_programs: list[str], clean_subjects: list[str]) -> None:
    with open(DATA_PATH / "programs.txt", "w") as f:
        for clean_program in clean_programs:
            f.write(f"{MAIN_PAGE_URL}{clean_program}\n")

    with open(DATA_PATH / "subjects.txt", "w") as f:
        for clean_subject in clean_subjects:
            f.write(f"{MAIN_PAGE_URL}{clean_subject}\n")


def scrape_courses_links_from_subjects(subject_html_path: Path, programs: list[str]) -> list[str]:
    """
    Retrieve all the links from a subject page, then only keeps those that are not already in the programs list.
    """
    all_subject_htmls = os.listdir(subject_html_path)

    courses_links = []
    for subject_html in tqdm(all_subject_htmls, desc="Scraping courses links from subjects"):
        with open(subject_html_path / subject_html, "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith("/courses-and-programs/") and "subject" not in href:
                    course_link = f"{MAIN_PAGE_URL}{href.replace('/courses-and-programs', '')}"
                    courses_links.append(course_link)

    courses_links = set(courses_links).difference(set(programs))

    return list(courses_links)


def extract_course_data(course_page_html: str) -> dict[str, Any]:
    """
    Extract the course data from a course page.
    """
    soup = BeautifulSoup(course_page_html, "html.parser")
    course_code = soup.find("span", class_="field field--code")
    if course_code is not None:
        course_code = course_code.text.strip()
    else:
        course_code = ""
    # get the course name
    course_name = soup.find(
        "span",
        class_="field field--name-title field--type-string field--label-hidden",
    )
    if course_name is not None:
        course_name = course_name.text.strip()
    else:
        course_name = ""
    # course delivery type
    course_delivery_type = soup.find(
        "div",
        class_="field field--name-field-course-type field--type-entity-reference field--label-hidden field__items",
    )
    if course_delivery_type is not None:
        course_delivery_type = course_delivery_type.find_all("span")[  # type: ignore
            0
        ].text.strip()
    else:
        course_delivery_type = ""

    # prereqs
    prereqs = soup.find(
        "div",
        class_="field field--name-field-prerequisites field--type-text-long field--label-above",
    )
    if prereqs is not None:
        prereqs = prereqs.find("p").text.strip()  # type: ignore
    else:
        prereqs = ""
    # hours
    hours = soup.find(
        "div",
        class_="field field--name-field-hours field--type-decimal field--label-inline",
    )
    if hours is not None:
        hours = hours.find("div", class_="field__item").text.strip()  # type: ignore
    else:
        hours = ""
    # fees
    fees = soup.find(
        "div",
        class_="field field--name-field-fee field--type-decimal field--label-inline",
    )
    if fees is not None:
        fees = fees.find("div", class_="field__item").text.strip()  # type: ignore
    else:
        fees = ""
    # get the course description
    course_description = soup.find(
        "div",
        class_="field field--name-body field--type-text-with-summary field--label-hidden field__item",
    )
    if course_description is not None:
        course_description = course_description.find("p").text.strip()  # type: ignore
    else:
        course_description = ""
    # get the course sections for further processing
    raw_sections = soup.find_all(
        "section",
        class_="eck-entity course-info-wrapper",
    )
    course_sections = []
    for section in raw_sections:
        course_sections.append(section.text.strip())
    return {
        "course_code": course_code,
        "course_name": course_name,
        "course_delivery_type": course_delivery_type,
        "prereqs": prereqs,
        "hours": hours,
        "fees": fees,
        "course_description": course_description,
        "course_sections": course_sections,
    }


def scrape_course_data(course_link_file_path: Path) -> list[dict[str, Any]]:
    """
    Scrape the course data from the course link.
    """
    with open(course_link_file_path, "r") as f:
        courses_links = f.readlines()
        courses_links = [course_link.strip() for course_link in courses_links]

    from concurrent.futures import ThreadPoolExecutor

    def scrape_single_course(course_link):
        response = requests.get(course_link)
        if response.status_code != 200:
            logger.warning(f"Invalid course link: {course_link}")
            return None
        else:
            extracted_course_data = extract_course_data(response.text)
            extracted_course_data["course_link"] = course_link
            return extracted_course_data

    course_data = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(scrape_single_course, course_link) for course_link in courses_links]
        for future in tqdm(futures, desc="Scraping course data"):
            result = future.result()
            if result is not None:
                course_data.append(result)
    return course_data


def save_course_links_to_file(course_links: list[str]) -> None:
    """
    Save the course data to a file.
    """
    logger.info(f"Saving {len(course_links)} course links to a file")
    # dump course links to a file
    with open(DATA_PATH / "courses.txt", "w") as f:
        for course_link in course_links:
            if "/subject/" in course_link or "-program" in course_link:
                continue
            f.write(f"{course_link}\n")


def save_course_data_to_file(course_data: list[dict[str, Any]]) -> None:
    """
    Save the course data to a file.
    """
    logger.info(f"Saving {len(course_data)} course data to files")
    for course in course_data:
        if course.get("course_name") is not None and course.get("course_code") is not None:
            filename = course["course_code"] + " - " + course["course_name"]
        with open(DATA_PATH / "course_data" / f"{filename}.json", "w") as f:
            json.dump(course, f)


def extract_dates_from_course_data(course_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Process course data to extract the dates using cohere:
    i = 0
    for course in tqdm(course_data, desc="Processing course data"):
        if (
            course.get("course_name") is not None
            and course.get("course_code") is not None
            and len(course["course_code"]) > 0
            and len(course["course_sections"]) > 0
        ):
            logger.info(course["course_name"])
            logger.info(course["course_link"])

            try:
                extracted_schedules = extract_dates(course["course_sections"])
            except cohere.errors.TooManyRequestsError:
                logger.warning("Too many requests, sleeping for 61 seconds")
                time.sleep(61)
                extracted_schedules = extract_dates(course["course_sections"])

            cleaned_schedules = clean_response(extracted_schedules)
            course["cleaned_response_schedules"] = cleaned_schedules
            try:
                schedules = json.loads(cleaned_schedules)
            except json.JSONDecodeError:
                logging.error(f"Error parsing schedules for {course['course_name']}")
            try:
                schedules = literal_eval(cleaned_schedules)
            except ValueError:
                logging.error(f"Error parsing schedules for {course['course_name']}")
            course["schedules"] = schedules
            i += 1
        else:
            course["schedules"] = []

    return course_data


def main():
    # make sure the data directory exists
    if not DATA_PATH.exists():
        raise ValueError("Data directory does not exist")
    # if programs are already saved, load, if not, scrape:
    programs = extract_programs_from_main_page(MAIN_PAGE_URL)
    programs, responses = check_programs_validity(programs)
    clean_subjects, clean_programs = separate_subjects_and_programs(responses=responses, programs=programs)
    write_programs_and_subjects_to_files(clean_programs, clean_subjects)
    courses_links = scrape_courses_links_from_subjects(DATA_PATH / "subject_htmls", programs=programs)
    save_course_links_to_file(courses_links)
    course_data = scrape_course_data(DATA_PATH / "courses.txt")
    save_course_data_to_file(course_data)
    course_data = extract_dates_from_course_data(course_data)
    save_course_data_to_file(course_data)


def load_course_data(course_code: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Load the course data from the files.
    If course_code is provided, only load the course data for courses with that prefix.
    """
    course_data = []
    if course_code is not None:
        for file in os.listdir(DATA_PATH / "course_data"):
            if file.startswith(course_code) and file.endswith(".json"):
                with open(DATA_PATH / "course_data" / file, "r") as f:
                    course_data.append(json.load(f))
    else:
        for file in os.listdir(DATA_PATH / "course_data"):
            if not file.startswith(" -") and file.endswith(".json"):
                with open(DATA_PATH / "course_data" / file, "r") as f:
                    course_data.append(json.load(f))
    logger.info(f"Loaded {len(course_data)} course data")
    return course_data


if __name__ == "__main__":
    try:
        # main()
        course_data = load_course_data(course_code="HOSF")
        course_data = extract_dates_from_course_data(course_data)
        save_course_data_to_file(course_data)
    except Exception as e:
        logger.error(f"Error: {e}")
        import pdb

        pdb.post_mortem()
