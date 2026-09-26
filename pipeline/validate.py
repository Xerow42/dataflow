"""
Validation layer.

Turns a raw Open-Meteo JSON payload into a list of per-day dicts, flagging
(not silently dropping) rows that fail schema, type, or range checks.
Cleaning decides what to do with flagged rows; validation only detects.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from . import config

REQUIRED_DAILY_FIELDS = ["time"] + config.DAILY_VARIABLES


@dataclass
class ValidationResult:
    valid_rows: List[Dict[str, Any]] = field(default_factory=list)
    invalid_rows: List[Dict[str, Any]] = field(default_factory=list)  # each has "_errors"
    records_processed: int = 0


def _check_row(row: Dict[str, Any]) -> List[str]:
    errors = []

    for field_name in REQUIRED_DAILY_FIELDS:
        if field_name not in row:
            errors.append(f"missing field: {field_name}")

    if errors:
        return errors

    try:
        datetime.strptime(row["time"], "%Y-%m-%d")
    except (ValueError, TypeError):
        errors.append(f"invalid date: {row.get('time')!r}")

    numeric_fields = [f for f in config.DAILY_VARIABLES if f != "weather_code"]
    for f in numeric_fields:
        val = row.get(f)
        if val is not None and not isinstance(val, (int, float)):
            errors.append(f"non-numeric value for {f}: {val!r}")

    tmax, tmin = row.get("temperature_2m_max"), row.get("temperature_2m_min")
    if isinstance(tmax, (int, float)) and isinstance(tmin, (int, float)) and tmin > tmax:
        errors.append(f"temperature_2m_min ({tmin}) > temperature_2m_max ({tmax})")

    precip = row.get("precipitation_sum")
    if isinstance(precip, (int, float)) and precip < 0:
        errors.append(f"negative precipitation_sum: {precip}")

    wind = row.get("wind_speed_10m_max")
    if isinstance(wind, (int, float)) and wind < 0:
        errors.append(f"negative wind_speed_10m_max: {wind}")

    return errors


def validate_daily_payload(payload: Dict[str, Any]) -> ValidationResult:
    daily = payload.get("daily", {})
    times = daily.get("time", [])

    result = ValidationResult(records_processed=len(times))

    for i, day in enumerate(times):
        row = {"time": day}
        for f in config.DAILY_VARIABLES:
            values = daily.get(f, [])
            row[f] = values[i] if i < len(values) else None

        errors = _check_row(row)
        if errors:
            row["_errors"] = errors
            result.invalid_rows.append(row)
        else:
            result.valid_rows.append(row)

    return result
