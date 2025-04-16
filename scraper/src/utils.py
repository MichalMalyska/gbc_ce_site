import json
from pathlib import Path
from typing import Set


def load_processed_courses(data_path: Path) -> Set[str]:
    """Load set of course codes that have already been processed by LLMs"""
    processed_file = data_path / "processed_courses.json"
    if processed_file.exists():
        with open(processed_file, "r") as f:
            return set(json.load(f))
    return set()


def save_processed_courses(data_path: Path, processed: Set[str]) -> None:
    """Save set of processed course codes"""
    with open(data_path / "processed_courses.json", "w") as f:
        json.dump(list(processed), f)
