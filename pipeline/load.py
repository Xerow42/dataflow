"""
Load layer.

Writes a transformed DataFrame into the database with idempotent upserts,
keyed on (city_name, country, observation_date) so re-running the pipeline
for a date range that was already loaded updates existing rows instead of
duplicating them.

Supports two backends via DATABASE_URL (see pipeline/config.py):
  - sqlite:///path/to/file.db   -> used for local dev and for the automated
                                    tests in this repo (zero external
                                    services required).
  - postgresql://user:pass@host:port/dbname -> the target production
                                    backend, used by docker-compose.
"""
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import pandas as pd

from . import config

logger = logging.getLogger("dataflow.load")

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS locations (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_name   TEXT NOT NULL,
    country     TEXT NOT NULL,
    latitude    REAL,
    longitude   REAL,
    UNIQUE(city_name, country)
);

CREATE TABLE IF NOT EXISTS daily_weather (
    weather_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id            INTEGER NOT NULL REFERENCES locations(location_id),
    observation_date        TEXT NOT NULL,
    temp_max_c              REAL,
    temp_min_c              REAL,
    temp_mean_c             REAL,
    precipitation_mm        REAL,
    wind_speed_max_kmh      REAL,
    humidity_mean_pct       REAL,
    weather_code            INTEGER,
    season                  TEXT,
    is_weekend               INTEGER,
    temp_mean_7d_rolling    REAL,
    is_outlier                INTEGER DEFAULT 0,
    is_imputed                INTEGER DEFAULT 0,
    ingested_at                TEXT NOT NULL,
    UNIQUE(location_id, observation_date)
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_started_at      TEXT NOT NULL,
    run_finished_at      TEXT,
    records_processed    INTEGER,
    valid_records         INTEGER,
    duplicates_removed    INTEGER,
    invalid_records       INTEGER,
    outliers_flagged      INTEGER,
    status                 TEXT
);

CREATE INDEX IF NOT EXISTS idx_daily_weather_date ON daily_weather(observation_date);
CREATE INDEX IF NOT EXISTS idx_daily_weather_loc_date ON daily_weather(location_id, observation_date);
"""


def _is_sqlite(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def get_connection(database_url: Optional[str] = None):
    database_url = database_url or config.DATABASE_URL
    if _is_sqlite(database_url):
        path = database_url.replace("sqlite:///", "", 1)
        import os
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    else:
        try:
            import psycopg2  # noqa: imported lazily -- only required in Postgres mode
        except ImportError as exc:
            raise RuntimeError(
                "psycopg2 is required for a PostgreSQL DATABASE_URL. "
                "Install it with: pip install psycopg2-binary"
            ) from exc
        parsed = urlparse(database_url)
        return psycopg2.connect(
            dbname=parsed.path.lstrip("/"),
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
        )


def init_schema(conn, database_url: Optional[str] = None) -> None:
    database_url = database_url or config.DATABASE_URL
    if _is_sqlite(database_url):
        conn.executescript(SQLITE_SCHEMA)
        conn.commit()
    else:
        import os
        schema_path = os.path.join(os.path.dirname(__file__), "..", "sql", "schema_postgres.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            with conn.cursor() as cur:
                cur.execute(f.read())
        conn.commit()


def _get_or_create_location(conn, city_name: str, country: str, lat: float, lon: float,
                             database_url: Optional[str] = None) -> int:
    database_url = database_url or config.DATABASE_URL
    placeholder = "?" if _is_sqlite(database_url) else "%s"
    cur = conn.cursor()
    cur.execute(
        f"SELECT location_id FROM locations WHERE city_name = {placeholder} AND country = {placeholder}",
        (city_name, country),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    if _is_sqlite(database_url):
        cur.execute(
            "INSERT INTO locations (city_name, country, latitude, longitude) VALUES (?, ?, ?, ?)",
            (city_name, country, lat, lon),
        )
        conn.commit()
        return cur.lastrowid
    else:
        cur.execute(
            """INSERT INTO locations (city_name, country, latitude, longitude)
               VALUES (%s, %s, %s, %s) RETURNING location_id""",
            (city_name, country, lat, lon),
        )
        location_id = cur.fetchone()[0]
        conn.commit()
        return location_id


def _none_safe(val):
    if pd.isna(val):
        return None
    return val


def upsert_daily_weather(conn, df: pd.DataFrame, location_id: int,
                          database_url: Optional[str] = None) -> int:
    """Idempotent upsert: re-loading the same (location, date) updates the row."""
    database_url = database_url or config.DATABASE_URL
    ingested_at = datetime.now(timezone.utc).isoformat()
    cur = conn.cursor()
    rows_written = 0

    for _, r in df.iterrows():
        obs_date = r["observation_date"]
        obs_date_str = obs_date.strftime("%Y-%m-%d") if hasattr(obs_date, "strftime") else str(obs_date)

        params = (
            location_id, obs_date_str,
            _none_safe(r["temp_max_c"]), _none_safe(r["temp_min_c"]), _none_safe(r["temp_mean_c"]),
            _none_safe(r["precipitation_mm"]), _none_safe(r["wind_speed_max_kmh"]),
            _none_safe(r["humidity_mean_pct"]), _none_safe(r["weather_code"]),
            r["season"], bool(r["is_weekend"]), _none_safe(r["temp_mean_7d_rolling"]),
            bool(r["_outlier"]), bool(r["_imputed"]), ingested_at,
        )

        if _is_sqlite(database_url):
            cur.execute(
                """
                INSERT INTO daily_weather (
                    location_id, observation_date, temp_max_c, temp_min_c, temp_mean_c,
                    precipitation_mm, wind_speed_max_kmh, humidity_mean_pct, weather_code,
                    season, is_weekend, temp_mean_7d_rolling, is_outlier, is_imputed, ingested_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(location_id, observation_date) DO UPDATE SET
                    temp_max_c=excluded.temp_max_c,
                    temp_min_c=excluded.temp_min_c,
                    temp_mean_c=excluded.temp_mean_c,
                    precipitation_mm=excluded.precipitation_mm,
                    wind_speed_max_kmh=excluded.wind_speed_max_kmh,
                    humidity_mean_pct=excluded.humidity_mean_pct,
                    weather_code=excluded.weather_code,
                    season=excluded.season,
                    is_weekend=excluded.is_weekend,
                    temp_mean_7d_rolling=excluded.temp_mean_7d_rolling,
                    is_outlier=excluded.is_outlier,
                    is_imputed=excluded.is_imputed,
                    ingested_at=excluded.ingested_at
                """,
                params,
            )
        else:
            cur.execute(
                """
                INSERT INTO daily_weather (
                    location_id, observation_date, temp_max_c, temp_min_c, temp_mean_c,
                    precipitation_mm, wind_speed_max_kmh, humidity_mean_pct, weather_code,
                    season, is_weekend, temp_mean_7d_rolling, is_outlier, is_imputed, ingested_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (location_id, observation_date) DO UPDATE SET
                    temp_max_c=EXCLUDED.temp_max_c,
                    temp_min_c=EXCLUDED.temp_min_c,
                    temp_mean_c=EXCLUDED.temp_mean_c,
                    precipitation_mm=EXCLUDED.precipitation_mm,
                    wind_speed_max_kmh=EXCLUDED.wind_speed_max_kmh,
                    humidity_mean_pct=EXCLUDED.humidity_mean_pct,
                    weather_code=EXCLUDED.weather_code,
                    season=EXCLUDED.season,
                    is_weekend=EXCLUDED.is_weekend,
                    temp_mean_7d_rolling=EXCLUDED.temp_mean_7d_rolling,
                    is_outlier=EXCLUDED.is_outlier,
                    is_imputed=EXCLUDED.is_imputed,
                    ingested_at=EXCLUDED.ingested_at
                """,
                params,
            )
        rows_written += 1

    conn.commit()
    return rows_written


def record_pipeline_run(conn, started_at: str, finished_at: str, records_processed: int,
                         valid_records: int, duplicates_removed: int, invalid_records: int,
                         outliers_flagged: int, status: str,
                         database_url: Optional[str] = None) -> None:
    database_url = database_url or config.DATABASE_URL
    placeholder = "?" if _is_sqlite(database_url) else "%s"
    cur = conn.cursor()
    cur.execute(
        f"""INSERT INTO pipeline_runs (
            run_started_at, run_finished_at, records_processed, valid_records,
            duplicates_removed, invalid_records, outliers_flagged, status
        ) VALUES ({placeholder},{placeholder},{placeholder},{placeholder},
                   {placeholder},{placeholder},{placeholder},{placeholder})""",
        (started_at, finished_at, records_processed, valid_records,
         duplicates_removed, invalid_records, outliers_flagged, status),
    )
    conn.commit()
