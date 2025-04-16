import logging
import os

import cohere
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("COHERE_API_KEY")

co = cohere.Client(
    api_key=api_key,  # type: ignore
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

logger = logging.getLogger(__name__)


def cohere_extract_dates(course_sections: list[str]):
    if len(course_sections) == 0:
        logger.warning("No course sections provided")
        return ""
    prompt = f"""
    Extract and return in json format all schedule information from the following input.
    The response must be in this exact format:
    {{
        "schedules": [
            {{
                "start_date": "YYYY-MM-DD",
                "end_date": "YYYY-MM-DD",
                "day_or_days_of_week": "Full day names",
                "start_time": "HH:MM AM/PM",
                "end_time": "HH:MM AM/PM"
            }}
        ]
    }}

    Input text:
    {course_sections}
    """

    response = co.chat(
        model="command-r-08-2024",
        message=prompt,
        temperature=0.1,
        prompt_truncation="off",
        connectors=[],
        stream=False,
    )
    return response.text


def cohere_clean_response(response: str) -> str:
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
    print(cohere_extract_dates(course_data["course_sections"]))
