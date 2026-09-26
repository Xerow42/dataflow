"""
Ingestion layer.

Calls the real Open-Meteo historical archive API and writes an immutable
raw JSON snapshot to disk for every (location, date range) pull. Raw
snapshots are never modified in place -- later stages always read from
here and write their own output elsewhere (data/processed), so a bad
transform can always be re-run against the original response.
"""
import json
import logging
import os
import time
from datetime import date, datetime, timezone
from typing import Optional

import requests

from . import config

logger = logging.getLogger("dataflow.ingest")


class IngestionError(Exception):
    pass


def _raw_snapshot_path(city_name: str, start_date: str, end_date: str) -> str:
    os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
    fname = f"{city_name.lower()}_{start_date}_{end_date}.json"
    return os.path.join(config.RAW_DATA_DIR, fname)


def fetch_daily_weather(
    location: config.Location,
    start_date: str,
    end_date: str,
    session: Optional[requests.Session] = None,
    max_retries: int = 3,
    timeout: int = 30,
) -> dict:
    """
    Fetch daily weather for one location and date range from the real
    Open-Meteo archive API, with retry/backoff. Writes the raw response
    to data/raw/ before returning it, so ingestion always leaves an
    immutable audit trail even if a later stage fails.
    """
    session = session or requests.Session()
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(config.DAILY_VARIABLES),
        "timezone": config.TIMEZONE,
    }

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Fetching %s..%s for %s (attempt %d/%d)",
                start_date, end_date, location.city_name, attempt, max_retries,
            )
            resp = session.get(config.OPEN_METEO_ARCHIVE_URL, params=params, timeout=timeout)
            resp.raise_for_status()
            payload = resp.json()
            if "daily" not in payload:
                raise IngestionError(f"Unexpected response shape: missing 'daily' key: {payload}")

            path = _raw_snapshot_path(location.city_name, start_date, end_date)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "location": {
                            "city_name": location.city_name,
                            "country": location.country,
                            "latitude": location.latitude,
                            "longitude": location.longitude,
                        },
                        "source_url": resp.url,
                        "response": payload,
                    },
                    f,
                    indent=2,
                )
            logger.info("Wrote raw snapshot: %s", path)
            return payload

        except (requests.RequestException, IngestionError) as exc:
            last_error = exc
            logger.warning("Fetch attempt %d failed: %s", attempt, exc)
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # exponential backoff: 2s, 4s, ...

    raise IngestionError(
        f"Failed to fetch data for {location.city_name} after {max_retries} attempts: {last_error}"
    )


def load_raw_snapshot(path: str) -> dict:
    """Read back a previously saved raw snapshot (used by validate/clean/transform)."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ingest_all(locations, start_date: str, end_date: str) -> dict:
    """
    Ingest daily weather for a list of locations over one date range.
    Returns {city_name: raw_snapshot_path}. A failure on one city does not
    stop ingestion for the others -- each failure is logged and returned
    under the 'errors' key so the caller (run_pipeline.py) can decide how
    to proceed.
    """
    results = {}
    errors = {}
    session = requests.Session()
    for loc in locations:
        try:
            fetch_daily_weather(loc, start_date, end_date, session=session)
            results[loc.city_name] = _raw_snapshot_path(loc.city_name, start_date, end_date)
        except IngestionError as exc:
            errors[loc.city_name] = str(exc)
            logger.error("Ingestion failed for %s: %s", loc.city_name, exc)
    return {"results": results, "errors": errors}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    today = date.today()
    start = today.replace(year=today.year - 1).isoformat()
    end = today.isoformat()
    summary = ingest_all(config.LOCATIONS, start, end)
    print(json.dumps(summary, indent=2))
