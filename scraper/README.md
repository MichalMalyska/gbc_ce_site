# GBC CE Scraper

## Scraping

To run a full scrape of all courses:

```bash

uv run python -m src.scrape --scrape

```

This will populate the `data/course_data` directory with JSON files.

If course JSON already exists, the scraper will reuse it unless you pass `--force`.

## Syncing Data

To sync the scraped data into Postgres:

```bash
uv run python -m db.load_data --json-dir ../data/course_data/
```

This command bootstraps an empty database schema if needed and then syncs by `course_code`:

- new `course_code`: insert course and schedules
- existing `course_code`: overwrite course fields and replace schedules
- missing from latest scrape: leave the existing database row untouched

During scrape reuse and DB sync, weekday values are normalized to canonical full names such as `Tuesday` or
`Tuesday, Thursday`. Self-paced or flexible schedules store `""`.

To do a clean rebuild against a fresh Neon database, pass `--reset` explicitly:

```bash
uv run python -m db.load_data --json-dir ../data/course_data/ --reset
```

## Configuration

Set `DATABASE_URL` to your target Postgres connection string. Neon, Supabase, and any standard Postgres vendor are supported.
