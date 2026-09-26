"""
Transformation layer.

Converts cleaned row dicts into a tabular pandas DataFrame ready for
loading, and derives a small number of explainable fields (season,
weekend flag, 7-day rolling mean temperature). No new facts are invented --
everything here is a deterministic function of fields already present.
"""
from typing import Any, Dict, List

import pandas as pd


def _season_for_month(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def rows_to_dataframe(rows: List[Dict[str, Any]], city_name: str, country: str) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["observation_date"] = pd.to_datetime(df["time"])
    df["city_name"] = city_name
    df["country"] = country

    df = df.rename(
        columns={
            "temperature_2m_max": "temp_max_c",
            "temperature_2m_min": "temp_min_c",
            "temperature_2m_mean": "temp_mean_c",
            "precipitation_sum": "precipitation_mm",
            "wind_speed_10m_max": "wind_speed_max_kmh",
            "relative_humidity_2m_mean": "humidity_mean_pct",
        }
    )

    df["season"] = df["observation_date"].dt.month.apply(_season_for_month)
    df["is_weekend"] = df["observation_date"].dt.dayofweek >= 5

    df = df.sort_values("observation_date")
    df["temp_mean_7d_rolling"] = df["temp_mean_c"].rolling(window=7, min_periods=1).mean()

    keep_cols = [
        "city_name", "country", "observation_date",
        "temp_max_c", "temp_min_c", "temp_mean_c",
        "precipitation_mm", "wind_speed_max_kmh", "humidity_mean_pct",
        "weather_code", "season", "is_weekend", "temp_mean_7d_rolling",
        "_outlier", "_imputed",
    ]
    for col in keep_cols:
        if col not in df.columns:
            df[col] = False if col in ("_outlier", "_imputed") else None

    return df[keep_cols].reset_index(drop=True)
