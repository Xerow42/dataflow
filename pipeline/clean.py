"""
Cleaning layer.

Input: list of valid row dicts from validate.py (already passed schema/type
checks). This stage removes duplicates, flags statistical outliers (it does
not silently delete them -- they are kept but marked, since an unusually
hot or rainy day is legitimate data, not necessarily an error), and decides
what happens to rows with missing values.
"""
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List

from . import config

logger = logging.getLogger("dataflow.clean")


@dataclass
class CleaningResult:
    clean_rows: List[Dict[str, Any]] = field(default_factory=list)
    duplicates_removed: int = 0
    outliers_flagged: int = 0
    rows_with_imputed_values: int = 0


def remove_duplicates(rows: List[Dict[str, Any]]):
    seen = set()
    deduped = []
    removed = 0
    for row in rows:
        key = row["time"]
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        deduped.append(row)
    return deduped, removed


def _is_outlier(row: Dict[str, Any]) -> bool:
    tmax = row.get("temperature_2m_max")
    tmin = row.get("temperature_2m_min")
    precip = row.get("precipitation_sum")

    if isinstance(tmax, (int, float)) and tmax > config.OUTLIER_TEMP_MAX_C:
        return True
    if isinstance(tmin, (int, float)) and tmin < config.OUTLIER_TEMP_MIN_C:
        return True
    if isinstance(precip, (int, float)) and precip > config.OUTLIER_PRECIP_MAX_MM:
        return True
    return False


def _impute_missing(rows: List[Dict[str, Any]]) -> int:
    """
    Fill only isolated missing days that have non-missing adjacent calendar
    days. Never propagate a known value through a multi-day gap or an edge.
    """
    imputed_count = 0
    rows.sort(key=lambda row: row["time"])
    missing_indices = [i for i, row in enumerate(rows)
                       if row.get("temperature_2m_mean") is None]
    for i in missing_indices:
        if i == 0 or i == len(rows) - 1:
            continue
        previous, current, following = rows[i - 1], rows[i], rows[i + 1]
        if previous.get("temperature_2m_mean") is None or following.get("temperature_2m_mean") is None:
            continue
        previous_date = date.fromisoformat(previous["time"])
        current_date = date.fromisoformat(current["time"])
        next_date = date.fromisoformat(following["time"])
        if current_date - previous_date != timedelta(days=1) or next_date - current_date != timedelta(days=1):
            continue
        current["temperature_2m_mean"] = previous["temperature_2m_mean"]
        current["_imputed"] = True
        imputed_count += 1
    return imputed_count


def clean_rows(rows: List[Dict[str, Any]]) -> CleaningResult:
    # Do not mutate validation results held by callers.
    deduped, dup_count = remove_duplicates([dict(row) for row in rows])

    outlier_count = 0
    for row in deduped:
        row["_outlier"] = _is_outlier(row)
        if row["_outlier"]:
            outlier_count += 1

    imputed_count = _impute_missing(deduped)

    for row in deduped:
        row.setdefault("_imputed", False)

    logger.info(
        "Cleaning: %d duplicates removed, %d outliers flagged, %d values imputed",
        dup_count, outlier_count, imputed_count,
    )

    return CleaningResult(
        clean_rows=deduped,
        duplicates_removed=dup_count,
        outliers_flagged=outlier_count,
        rows_with_imputed_values=imputed_count,
    )
