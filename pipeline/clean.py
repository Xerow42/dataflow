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
    Single-day gaps in temperature_2m_mean are forward-filled from the
    previous day (documented, conservative choice -- suitable for daily
    climate data with rare, isolated gaps). Rows are expected to already
    be sorted by date coming out of the Open-Meteo response.
    """
    imputed_count = 0
    last_known = None
    for row in rows:
        if row.get("temperature_2m_mean") is None and last_known is not None:
            row["temperature_2m_mean"] = last_known
            row["_imputed"] = True
            imputed_count += 1
        elif row.get("temperature_2m_mean") is not None:
            last_known = row["temperature_2m_mean"]
    return imputed_count


def clean_rows(rows: List[Dict[str, Any]]) -> CleaningResult:
    deduped, dup_count = remove_duplicates(rows)

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
