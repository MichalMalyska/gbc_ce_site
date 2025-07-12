# GBC CE Scraper

## Scraping

To run a full scrape of all courses:

```bash

uv run python -m src.scrape --scrape

```

This will populate the `data/course_data` directory with JSON files.

## Loading Data

To load the scraped data into the database:

```bash
uv run python -m db.load_data --json-dir ../data/course_data/
```

**Note:** This is a destructive operation. It will drop and recreate the `courses` and `schedules` tables in your database.
