import json
import logging
import os
from pathlib import Path
from typing import Any, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm

from .cerebras_extract_dates import cerebras_clean_response, cerebras_extract_dates  # noqa
from .cohere_extract_dates import cohere_clean_response, cohere_extract_dates  # noqa
from .constants import MAIN_PAGE_URL
from .filters import filter_courses
from .utils import load_processed_courses, save_processed_courses

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=Path(__file__).parent.parent / "logs" / "scrape.log",
)
logger = logging.getLogger()

DATA_PATH = Path(__file__).parent.parent.parent / "data"


def extract_programs_from_main_page(main_site_link: str) -> set[str]:
    """
    Extract unique program links from the main page.

    Args:
        main_site_link str: The main site URL

    Returns:
        set[str]: A set of unique program links
    """
    try:
        response = requests.get(main_site_link)
        soup = BeautifulSoup(response.text, "html.parser")
        programs = set()
        for link in tqdm(soup.find_all("a", href=True), desc="Extracting programs from main page"):
            href = link["href"]
            if href.startswith("/courses-and-programs/"):
                programs.add(href)
        return programs
    except Exception as e:
        logger.error(f"Failed to extract programs from {main_site_link}: {e}")
        return set()


def check_programs_validity(programs: set[str]) -> tuple[set[str], list[requests.Response]]:
    """
    Check the validity of programs and return valid ones
    """
    # Remove the "courses-and-programs" part of the link
    programs = {program.replace("courses-and-programs/", "") for program in programs}
    responses = []
    valid_programs = set()

    for program in tqdm(programs, desc="Checking program links validity"):
        link = f"{MAIN_PAGE_URL}{program}"
        try:
            response = requests.get(link)
            if response.status_code == 200:
                valid_programs.add(program)
                responses.append(response)
            else:
                logger.warning(f"Invalid program: {link}")
        except Exception as e:
            logger.error(f"Error checking program {link}: {e}")

    return valid_programs, responses


def separate_subjects_and_programs(responses: list[requests.Response], programs: set[str]) -> tuple[set[str], set[str]]:
    """Separate subjects and programs into unique sets"""
    clean_subjects = set()
    clean_programs = set()

    for response, program in zip(responses, programs):
        program_name = program.split("/")[-1]
        if "subject" in program:
            clean_subjects.add(program)
            with open(DATA_PATH / "subject_htmls" / f"{program_name}.html", "w") as f:
                f.write(response.text)
        elif not program.endswith("-programs"):
            clean_programs.add(program)
            with open(DATA_PATH / "program_htmls" / f"{program_name}.html", "w") as f:
                f.write(response.text)
        else:
            logger.warning(f"Skipping program: {program}")

    return clean_subjects, clean_programs


def write_programs_and_subjects_to_files(clean_programs: set[str], clean_subjects: set[str]) -> None:
    """Write unique programs and subjects to files"""
    with open(DATA_PATH / "programs.txt", "w") as f:
        for clean_program in sorted(clean_programs):
            f.write(f"{MAIN_PAGE_URL}{clean_program}\n")

    with open(DATA_PATH / "subjects.txt", "w") as f:
        for clean_subject in sorted(clean_subjects):
            f.write(f"{MAIN_PAGE_URL}{clean_subject}\n")


def scrape_courses_links_from_subjects(subject_html_path: Path, programs: set[str]) -> set[str]:
    """
    Retrieve unique course links from subject pages
    """
    all_subject_htmls = os.listdir(subject_html_path)
    courses_links = set()

    for subject_html in tqdm(all_subject_htmls, desc="Scraping courses links from subjects"):
        with open(subject_html_path / subject_html, "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith("/courses-and-programs/") and "subject" not in href:
                    course_link = f"{MAIN_PAGE_URL}{href.replace('/courses-and-programs', '')}"
                    courses_links.add(course_link)

    return courses_links - programs  # Remove any programs from the course links


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


def save_raw_course_links(course_links: set[str]) -> None:
    """Save all course links before filtering"""
    logger.info(f"Saving {len(course_links)} raw course links")
    try:
        with open(DATA_PATH / "raw_courses.txt", "w", encoding="utf-8") as f:
            for link in sorted(course_links):
                f.write(f"{link}\n")
        logger.info("Successfully saved raw course links")
    except Exception as e:
        logger.error(f"Error saving raw course links: {e}")
        raise


def save_course_links_to_file(course_links: set[str]) -> None:
    """Save unique course links to a file"""
    logger.info(f"Found {len(course_links)} total course links")
    valid_links = set()

    # First try to load existing raw links if we're not starting fresh
    raw_links_path = DATA_PATH / "raw_courses.txt"
    if raw_links_path.exists():
        logger.info("Found existing raw course links")
        with open(raw_links_path, "r", encoding="utf-8") as f:
            course_links = {line.strip() for line in f}
        logger.info(f"Loaded {len(course_links)} raw course links")

    for course_link in course_links:
        # Skip links that end with -program or -programs or contain /subject/
        if course_link.endswith("-program") or course_link.endswith("-programs") or "/subject/" in course_link:
            logger.debug(f"Skipping non-course link: {course_link}")
            continue

        # Remove the base URL part for cleaner storage
        clean_link = course_link.replace("https://coned.georgebrown.ca/courses-and-programs/", "")
        # Remove any leading/trailing slashes
        clean_link = clean_link.strip("/")

        if clean_link:  # Only add non-empty links
            valid_links.add(clean_link)

    try:
        logger.info(f"Saving {len(valid_links)} valid course links to file")
        # Ensure the data directory exists
        DATA_PATH.mkdir(parents=True, exist_ok=True)

        # Write the links
        with open(DATA_PATH / "courses.txt", "w", encoding="utf-8") as f:
            for link in sorted(valid_links):
                f.write(f"{link}\n")

        # Verify the file was written
        if (DATA_PATH / "courses.txt").exists():
            with open(DATA_PATH / "courses.txt", "r", encoding="utf-8") as f:
                written_count = len(f.readlines())
            logger.info(f"Successfully wrote {written_count} course links to file")
        else:
            logger.error("Failed to create courses.txt file")

    except Exception as e:
        logger.error(f"Error saving course links to file: {e}")
        raise


def scrape_course_data(course_link_file_path: Path) -> list[dict[str, Any]]:
    """
    Scrape the course data from the course link.
    """
    with open(course_link_file_path, "r") as f:
        courses_links = f.readlines()
        # Add the missing slash after courses-and-programs
        courses_links = [f"{MAIN_PAGE_URL}/{link.strip()}" for link in courses_links]

    logger.info(f"Scraping {len(courses_links)} courses")

    from concurrent.futures import ThreadPoolExecutor

    def scrape_single_course(course_link):
        try:
            response = requests.get(course_link)
            if response.status_code != 200:
                logger.warning(f"Invalid course link: {course_link}")
                return None
            else:
                extracted_course_data = extract_course_data(response.text)
                extracted_course_data["course_link"] = course_link
                return extracted_course_data
        except Exception as e:
            logger.error(f"Error scraping {course_link}: {e}")
            return None

    course_data = []
    with ThreadPoolExecutor(max_workers=10) as executor:  # Limit concurrent requests
        futures = [executor.submit(scrape_single_course, course_link) for course_link in courses_links]
        for future in tqdm(futures, desc="Scraping course data"):
            result = future.result()
            if result is not None:
                course_data.append(result)

    logger.info(f"Successfully scraped {len(course_data)} courses")
    return course_data


def save_course_data_to_file(course_data: list[dict[str, Any]]) -> None:
    """
    Save the course data to a file.
    """
    logger.info(f"Saving {len(course_data)} course data to files")
    saved = 0
    skipped = 0

    for course in course_data:
        # Skip courses without both name and code
        if not course.get("course_name") or not course.get("course_code"):
            skipped += 1
            continue

        # Skip programs
        if "program" in course.get("course_name", "").lower():
            skipped += 1
            continue

        try:
            filename = f"{course['course_code']} - {course['course_name']}"
            with open(DATA_PATH / "course_data" / f"{filename}.json", "w") as f:
                json.dump(course, f)
            saved += 1
        except Exception as e:
            logger.error(f"Error saving course {course.get('course_name', 'UNKNOWN')}: {e}")
            skipped += 1

    logger.info(f"Successfully saved {saved} courses, skipped {skipped} invalid entries")


def try_extract_dates(course_sections: list[str], service: str = "cerebras") -> Optional[dict]:
    """Try to extract dates using specified service with exponential backoff"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),  # Increased multiplier for more aggressive backoff
        reraise=True,
    )
    def _extract():
        if service == "cerebras":
            return cerebras_extract_dates(course_sections)
        else:
            return cohere_extract_dates(course_sections)

    try:
        return _extract()  # type: ignore
    except Exception as e:
        logger.error(f"Failed to extract dates using {service}: {e}")
        return None


def clean_invalid_courses(course_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove courses without course codes and program entries"""
    valid_courses = []
    removed = 0

    for course in course_data:
        # Skip courses without course codes or that are programs
        if not course.get("course_code"):
            logger.debug(f"Removing course without code: {course.get('course_name', 'UNKNOWN')}")
            removed += 1
            continue

        # Skip if course name contains "program" (case insensitive)
        if "program" in course.get("course_name", "").lower():
            logger.debug(f"Removing program: {course.get('course_name')}")
            removed += 1
            continue

        valid_courses.append(course)

    logger.info(f"Removed {removed} invalid courses, kept {len(valid_courses)} valid courses")
    return valid_courses


def extract_dates_from_course_data(
    course_data: list[dict[str, Any]], resume: bool = True
) -> Tuple[list[dict[str, Any]], Set[str]]:
    """
    Extract dates from course data with resume capability and rate limiting
    """
    # Clean invalid courses first
    course_data = clean_invalid_courses(course_data)

    processed_courses = load_processed_courses(DATA_PATH) if resume else set()
    logger.info(f"Starting with {len(processed_courses)} previously processed courses")

    # Get unprocessed courses
    unprocessed = [c for c in course_data if c.get("course_code") not in processed_courses]
    logger.info(f"Found {len(unprocessed)} courses that need processing")

    no_sections = 0
    processed_with_schedules = 0
    processed_without_schedules = 0

    # Only process unprocessed courses
    for course in tqdm(unprocessed, desc="Processing unprocessed courses"):
        course_code = course.get("course_code", "")

        # Initialize schedules if not present
        if "schedules" not in course:
            course["schedules"] = []

        # Check if course has sections to process
        if not course.get("course_sections"):
            logger.debug(f"No sections to process for {course_code}: {course.get('course_name')}")
            processed_courses.add(course_code)
            no_sections += 1
            continue

        logger.info(f"Processing {course_code}: {course.get('course_name')}")

        # Try Cerebras first
        extracted_schedules = try_extract_dates(course["course_sections"], service="cerebras")

        if extracted_schedules:
            cleaned_schedules = cerebras_clean_response(extracted_schedules)  # type: ignore
            course["schedules"] = cleaned_schedules
            course["cleaned_response_schedules"] = json.dumps({"schedules": cleaned_schedules})
            logger.debug(f"Successfully extracted schedules using Cerebras for {course_code}")
            processed_with_schedules += 1
        else:
            # Fallback to Cohere
            cohere_response = try_extract_dates(course["course_sections"], service="cohere")

            if cohere_response:
                try:
                    cleaned_response = cohere_clean_response(cohere_response)  # type: ignore
                    course["cleaned_response_schedules"] = cleaned_response
                    cleaned_schedules = json.loads(cleaned_response)
                    if isinstance(cleaned_schedules, dict) and "schedules" in cleaned_schedules:
                        course["schedules"] = cleaned_schedules["schedules"]
                        logger.debug(f"Successfully extracted schedules using Cohere for {course_code}")
                        processed_with_schedules += 1
                    else:
                        logger.debug(f"Invalid schedule format for {course_code}")
                        course["schedules"] = []
                        processed_without_schedules += 1
                except json.JSONDecodeError:
                    logger.debug(f"Failed to parse schedules for {course_code}")
                    course["schedules"] = []
                    processed_without_schedules += 1
            else:
                processed_without_schedules += 1

        # Mark as processed
        processed_courses.add(course_code)
        # Save progress periodically
        if len(processed_courses) % 10 == 0:
            save_processed_courses(DATA_PATH, processed_courses)
            logger.info(
                f"Progress: {len(processed_courses)} courses processed "
                f"({no_sections} no sections, "
                f"{processed_with_schedules} with schedules, "
                f"{processed_without_schedules} without schedules)"
            )

    # Save final state
    save_processed_courses(DATA_PATH, processed_courses)
    logger.info(
        f"Completed processing {len(processed_courses)} courses:\n"
        f"- {no_sections} courses had no sections to process\n"
        f"- {processed_with_schedules} courses processed successfully with schedules\n"
        f"- {processed_without_schedules} courses processed but no schedules found"
    )
    return course_data, processed_courses


def main():
    # make sure the data directory exists
    if not DATA_PATH.exists():
        DATA_PATH.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created data directory: {DATA_PATH}")

    # Create required subdirectories
    ensure_data_directories()

    # Check if we already have course data
    existing_courses = list(DATA_PATH.glob("course_data/*.json"))
    if existing_courses:
        logger.info(f"Found {len(existing_courses)} existing course files")
        if input("Course data already exists. Do you want to re-scrape? (y/N): ").lower() != "y":
            logger.info("Skipping scrape, using existing course data")
            course_data = load_course_data()
            course_data, processed = extract_dates_from_course_data(course_data, resume=True)
            save_course_data_to_file(course_data)
            logger.info(f"Processed {len(processed)} courses")
            return

    # Check if we need to scrape or can use existing raw links
    raw_links_path = DATA_PATH / "raw_courses.txt"
    if not raw_links_path.exists():
        # Scrape programs and subjects
        programs = extract_programs_from_main_page(MAIN_PAGE_URL)
        programs, responses = check_programs_validity(programs)
        clean_subjects, clean_programs = separate_subjects_and_programs(responses=responses, programs=programs)
        write_programs_and_subjects_to_files(clean_programs, clean_subjects)

        # Scrape course links
        courses_links = scrape_courses_links_from_subjects(DATA_PATH / "subject_htmls", programs=programs)
        # Save raw links first
        save_raw_course_links(courses_links)
    else:
        logger.info("Using existing raw course links")
        with open(raw_links_path, "r", encoding="utf-8") as f:
            courses_links = {line.strip() for line in f}

    # Filter and save valid course links
    save_course_links_to_file(courses_links)

    # Verify courses.txt was created
    if not (DATA_PATH / "courses.txt").exists():
        logger.error("courses.txt was not created. Stopping.")
        return

    # Continue with course data scraping
    course_data = scrape_course_data(DATA_PATH / "courses.txt")
    save_course_data_to_file(course_data)
    course_data, processed = extract_dates_from_course_data(course_data, resume=False)
    save_course_data_to_file(course_data)
    logger.info(f"Processed {len(processed)} courses")


def ensure_data_directories():
    """Ensure all required data directories exist"""
    directories = [
        DATA_PATH,
        DATA_PATH / "course_data",
        DATA_PATH / "subject_htmls",
        DATA_PATH / "program_htmls",
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")


def load_course_data(course_code: Optional[str] = None, test_mode: bool = False) -> list[dict[str, Any]]:
    """
    Load the course data from the files.
    """
    ensure_data_directories()

    course_data = []
    files_to_process = []

    try:
        files_to_process = [
            f for f in os.listdir(DATA_PATH / "course_data") if f.endswith(".json") and not f.startswith(" -")
        ]
        logger.info(f"Found {len(files_to_process)} total course files")
    except Exception as e:
        logger.error(f"Error listing course files: {e}")
        return []

    # In test mode, just take the first few files
    if test_mode:
        files_to_process = files_to_process[:4]  # Take first 4 files
        logger.info(f"Test mode: using files: {files_to_process}")

    if course_code is not None:
        files_to_process = [f for f in files_to_process if f.startswith(course_code)]

    for file in files_to_process:
        try:
            with open(DATA_PATH / "course_data" / file, "r") as f:
                course_data.append(json.load(f))
        except Exception as e:
            logger.error(f"Error loading {file}: {e}")
            continue

    logger.info(f"Loaded {len(course_data)} course data" + (" (TEST MODE)" if test_mode else ""))
    return course_data


def find_courses(
    subject: Optional[str] = None,
    day: Optional[str] = None,
    after_time: Optional[str] = None,
    before_time: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Load and filter courses based on criteria

    Args:
        subject: Subject keyword to search for
        day: Day of week to filter by
        after_time: Only show courses starting after this time (24h format HH:MM)
        before_time: Only show courses starting before this time (24h format HH:MM)

    Returns:
        List of matching courses
    """
    courses = load_course_data()
    return filter_courses(courses, subject=subject, day=day, after_time=after_time, before_time=before_time)


def reprocess_course_schedules(course_data: dict) -> dict:
    """Reprocess course sections to extract schedules"""
    if not course_data.get("course_sections"):
        return course_data

    try:
        # Try Cerebras first
        extracted_schedules = try_extract_dates(course_data["course_sections"], service="cerebras")

        if extracted_schedules:
            cleaned_schedules = cerebras_clean_response(extracted_schedules)  # type: ignore
            course_data["schedules"] = cleaned_schedules
            course_data["cleaned_response_schedules"] = json.dumps({"schedules": cleaned_schedules})
        else:
            # Fallback to Cohere
            cohere_response = try_extract_dates(course_data["course_sections"], service="cohere")

            if cohere_response:
                cleaned_response = cohere_clean_response(cohere_response)  # type: ignore
                course_data["cleaned_response_schedules"] = cleaned_response
                cleaned_schedules = json.loads(cleaned_response)
                if isinstance(cleaned_schedules, dict) and "schedules" in cleaned_schedules:
                    course_data["schedules"] = cleaned_schedules["schedules"]

    except Exception as e:
        logger.error(f"Error reprocessing schedules for {course_data.get('course_code')}: {e}")

    return course_data


if __name__ == "__main__":
    try:
        # Add argument parsing
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--test", action="store_true", help="Run in test mode with small dataset")
        parser.add_argument("--scrape", action="store_true", help="Scrape new course data")
        parser.add_argument("--force", action="store_true", help="Force re-scrape even if data exists")
        args = parser.parse_args()

        if args.scrape:
            # Check for existing data unless force flag is used
            existing_courses = list(DATA_PATH.glob("course_data/*.json"))
            if existing_courses and not args.force:
                logger.info(f"Found {len(existing_courses)} existing course files")
                logger.info("Use --force to re-scrape")
                exit(0)
            # Run the full scraping process
            main()
        else:
            # Just process existing data
            course_data = load_course_data(test_mode=args.test)
            if not course_data:
                logger.error("No course data found. Try running with --scrape to get course data first")
                exit(1)

            updated_data, processed = extract_dates_from_course_data(
                course_data,
                resume=True,
            )
            save_course_data_to_file(updated_data)
            logger.info(f"Processed {len(processed)} courses")
    except Exception as e:
        logger.error(f"Error: {e}")
        import pdb

        pdb.post_mortem()
