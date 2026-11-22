"""
Validation layer.

Turns a raw Open-Meteo JSON payload into a list of per-day dicts, flagging
(not silently dropping) rows that fail schema, type, or range checks.
Cleaning decides what to do with flagged rows; validation only detects.
"""
from dataclasses import dataclass, field
from datetime import datetime
import math
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
        if val is not None and (
            isinstance(val, bool)
            or not isinstance(val, (int, float))
            or not math.isfinite(val)
        ):
            errors.append(f"invalid numeric value for {f}: {val!r}")

    code = row.get("weather_code")
    if code is not None and (isinstance(code, bool) or not isinstance(code, int)):
        errors.append(f"invalid weather_code: {code!r}")

    tmax, tmin = row.get("temperature_2m_max"), row.get("temperature_2m_min")
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
           for v in (tmax, tmin)) and tmin > tmax:
        errors.append(f"temperature_2m_min ({tmin}) > temperature_2m_max ({tmax})")

    humidity = row.get("relative_humidity_2m_mean")
    if isinstance(humidity, (int, float)) and not isinstance(humidity, bool) and math.isfinite(humidity):
        if not 0 <= humidity <= 100:
            errors.append(f"humidity outside 0..100: {humidity}")

    precip = row.get("precipitation_sum")
    if isinstance(precip, (int, float)) and precip < 0:
        errors.append(f"negative precipitation_sum: {precip}")

    wind = row.get("wind_speed_10m_max")
    if isinstance(wind, (int, float)) and wind < 0:
        errors.append(f"negative wind_speed_10m_max: {wind}")

    return errors


def validate_daily_payload(payload: Dict[str, Any]) -> ValidationResult:
    daily = payload.get("daily")
    if not isinstance(daily, dict) or not isinstance(daily.get("time"), list):
        raise ValueError("Weather payload must contain a daily object with a time array")
    times = daily["time"]
    if not times:
        raise ValueError("Weather payload contains no daily observations")

    result = ValidationResult(records_processed=len(times))

    for i, day in enumerate(times):
        row = {"time": day}
        structural_errors = []
        for f in config.DAILY_VARIABLES:
            if f not in daily:
                row[f] = None
                structural_errors.append(f"missing field: {f}")
                continue
            values = daily[f]
            if not isinstance(values, list):
                row[f] = None
                structural_errors.append(f"field {f} must be an array")
                continue
            if len(values) != len(times):
                structural_errors.append(
                    f"field {f} contains {len(values)} values; expected {len(times)}"
                )
            row[f] = values[i] if i < len(values) else None

        errors = structural_errors + _check_row(row)
        if errors:
            row["_errors"] = errors
            result.invalid_rows.append(row)
        else:
            result.valid_rows.append(row)

    return result
