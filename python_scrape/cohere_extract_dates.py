import logging
import os

import cohere
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("COHERE_API_KEY")
co = cohere.Client(
    api_key=api_key,
)

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "schedules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "day_or_days_of_week": {"type": "string"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                },
                "required": ["start_date", "end_date", "day_or_days_of_week", "start_time", "end_time"],
            },
        },
    },
    "required": ["schedules"],
}

RESPONSE_FORMAT = cohere.JsonObjectResponseFormat(schema_=JSON_SCHEMA)

logger = logging.getLogger(__name__)


def extract_dates(course_sections: list[str]):
    if len(course_sections) == 0:
        logger.warning("No course sections provided")
        return ""
    prompt = f"""
    I need you to extract and return in json format all of: \n* start date\n* end date\n* day / days of week\n* start time\n* end time\nFrom the following input:
    {course_sections}
    If some information is missing, return an empty string for that field. Make sure to include AM / PM in the time fields.
    """

    response = co.chat(
        model="command-r-08-2024",
        message=prompt,
        temperature=0.3,
        prompt_truncation="off",
        connectors=[],
        response_format=RESPONSE_FORMAT,
    )
    return response.text


def clean_response(response: str) -> str:
    """
    Cleans the response

    Args:
        response (str): response from cohere

    Returns:
        str: cleaned response
    """
    return (
        response.replace("```json", "")
        .replace("```", "")
        .strip()
        .replace("\n", "")
        .replace(" ", "")
        .replace("null", "None")
    )


if __name__ == "__main__":
    import json

    with open("data/course_data/HOSF 9489 - Preserving: Canning and Fermentation.json", "r") as f:
        course_data = json.load(f)
    print(extract_dates(course_data["course_sections"]))
