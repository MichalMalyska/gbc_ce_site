import logging
import os
from typing import Union

import instructor
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

api_key = os.getenv("CEREBRAS_API_KEY")

# Updated to use the current instructor API
client = instructor.patch(
    Cerebras(
        api_key=os.environ.get("CEREBRAS_API_KEY"),
    )
)


class Schedule(BaseModel):
    start_date: str
    end_date: str
    day_or_days_of_week: str
    start_time: str
    end_time: str


class ScheduleList(BaseModel):
    schedules: list[Schedule]


logger = logging.getLogger(__name__)


def cerebras_extract_dates(course_sections: list[str]) -> Union[ScheduleList, None]:
    if len(course_sections) == 0:
        logger.warning("No course sections provided")
        return None

    # Standardize the prompt to enforce consistent formatting
    prompt = f"""
    Extract and return in json format all schedule information from the following input.
    For each schedule entry, provide:
    * start_date: in YYYY-MM-DD format
    * end_date: in YYYY-MM-DD format
    * day_or_days_of_week: Full day names separated by commas (e.g., "Monday, Wednesday")
    * start_time: in 12-hour format with AM/PM (e.g., "9:00 AM")
    * end_time: in 12-hour format with AM/PM (e.g., "5:00 PM")
    
    Input text:
    {course_sections}
    
    If any information is missing, return an empty string for that field.
    """

    try:
        chat_completion = client.chat.completions.create(
            model="llama3.1-8b",
            response_model=ScheduleList,
            messages=[{"role": "user", "content": prompt}],
        )
        return chat_completion
    except Exception as e:
        logger.error(f"Error extracting dates: {e}")
        return None


def cerebras_clean_response(response: ScheduleList) -> dict[str, str]:
    """
    Cleans the response

    Args:
        response (ScheduleList): response from cerebras

    Returns:
        dict[str, str]: cleaned response
    """
    return response.model_dump()["schedules"]


if __name__ == "__main__":
    import json

    with open("data/course_data/HOSF 9489 - Preserving: Canning and Fermentation.json", "r") as f:
        course_data = json.load(f)
    extracted_dates = cerebras_extract_dates(course_data["course_sections"])
    if extracted_dates is not None:
        print(cerebras_clean_response(extracted_dates))
