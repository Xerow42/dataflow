"""
Central configuration for the DataFlow pipeline.

All values can be overridden with environment variables so the same code
runs locally, in tests, and in Docker without modification.
"""
import os
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Location:
    city_name: str
    country: str
    latitude: float
    longitude: float


# Lille is the primary MVP city. Paris and Marseille were added once the
# Lille MVP was validated (config-driven -- no other code changes were
# needed to add them; see Decision #6).
LOCATIONS: List[Location] = [
    Location(city_name="Lille", country="France", latitude=50.6292, longitude=3.0573),
    Location(city_name="Paris", country="France", latitude=48.8566, longitude=2.3522),
    Location(city_name="Marseille", country="France", latitude=43.2965, longitude=5.3698),
]

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

DAILY_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "wind_speed_10m_max",
    "relative_humidity_2m_mean",
    "weather_code",
]

TIMEZONE = "Europe/Paris"

RAW_DATA_DIR = os.environ.get(
    "RAW_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data", "raw")
)
PROCESSED_DATA_DIR = os.environ.get(
    "PROCESSED_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data", "processed")
)

# Database connection.
# - PostgreSQL in production / docker-compose (the target design):
#     postgresql://dataflow:dataflow@localhost:5432/dataflow
# - SQLite for local/dev/test runs with zero external services:
#     sqlite:///./data/dataflow.db
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/dataflow.db")

# Outlier detection thresholds (simple, explainable IQR-style rule).
OUTLIER_TEMP_MIN_C = -25.0
OUTLIER_TEMP_MAX_C = 45.0
OUTLIER_PRECIP_MAX_MM = 200.0
