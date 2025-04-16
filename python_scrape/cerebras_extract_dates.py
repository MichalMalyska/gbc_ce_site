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
        api_key=api_key,
    )  # type: ignore
)  # type: ignore


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

    prompt = f"""
    Extract schedule information from this input and return it in JSON format.
    ONLY return the JSON object, no other text.

    Required format:
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

    try:
        chat_completion = client.chat.completions.create(
            model="llama3.1-8b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Lower temperature for more consistent formatting
        )
        response_text = chat_completion.choices[0].message.content

        # Clean up the response text
        response_text = response_text.replace("```json", "").replace("```", "").strip()

        # Try to parse and validate
        return ScheduleList.model_validate_json(response_text)
    except Exception as e:
        logger.error(f"Error extracting dates: {e}")
        if response_text:
            logger.error(f"Raw response: {response_text}")
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
