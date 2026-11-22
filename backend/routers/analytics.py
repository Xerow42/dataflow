"""
Analytics endpoints. Reads only from the database -- never touches the
Open-Meteo API directly (that's the pipeline's job). Aggregation across
backends (SQLite for dev/test, PostgreSQL in production) is done in Python
with pandas rather than backend-specific SQL, so the same code works
against either DATABASE_URL.
"""
from datetime import date
import math
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db, placeholder

router = APIRouter(prefix="/api", tags=["analytics"])


def _check_date_range(start: date, end: date) -> None:
    if start > end:
        raise HTTPException(status_code=422, detail="start must not be later than end")


def _rounded_or_none(value):
    if pd.isna(value) or not math.isfinite(float(value)):
        return None
    return round(float(value), 2)


def _complete_precipitation_sum(values: pd.Series):
    """An unknown day makes a period's precipitation total unknown."""
    if values.empty or values.isna().any():
        return float("nan")
    return values.sum()


def _fetch_daily_df(conn, city: str, start_date: str, end_date: str) -> pd.DataFrame:
    ph = placeholder()
    query = f"""
        SELECT dw.observation_date, dw.temp_max_c, dw.temp_min_c, dw.temp_mean_c,
               dw.precipitation_mm, dw.wind_speed_max_kmh, dw.humidity_mean_pct,
               dw.season, dw.is_weekend, dw.temp_mean_7d_rolling, dw.is_outlier
        FROM daily_weather dw
        JOIN locations l ON l.location_id = dw.location_id
        WHERE l.city_name = {ph} AND dw.observation_date BETWEEN {ph} AND {ph}
        ORDER BY dw.observation_date
    """
    df = pd.read_sql_query(query, conn, params=(city, start_date, end_date))
    if not df.empty:
        df["observation_date"] = pd.to_datetime(df["observation_date"])
    return df


@router.get("/categories")
def list_categories(conn=Depends(get_db)):
    cur = conn.cursor()
    cur.execute("""SELECT l.city_name, l.country,
                          MIN(dw.observation_date), MAX(dw.observation_date)
                   FROM locations l LEFT JOIN daily_weather dw
                     ON dw.location_id = l.location_id
                   GROUP BY l.location_id, l.city_name, l.country
                   ORDER BY l.city_name""")
    rows = cur.fetchall()
    return [{"city_name": r[0], "country": r[1],
             "start_date": str(r[2]) if r[2] is not None else None,
             "end_date": str(r[3]) if r[3] is not None else None}
            for r in rows]


@router.get("/metrics")
def get_metrics(
    city: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    conn=Depends(get_db),
):
    _check_date_range(start, end)
    df = _fetch_daily_df(conn, city, str(start), str(end))
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {city} in {start}..{end}")

    hottest_idx = df["temp_max_c"].idxmax() if df["temp_max_c"].notna().any() else None
    coldest_idx = df["temp_min_c"].idxmin() if df["temp_min_c"].notna().any() else None

    return {
        "city": city,
        "start": str(start),
        "end": str(end),
        "records": int(len(df)),
        "avg_temp_c": _rounded_or_none(df["temp_mean_c"].mean()),
        # A partial sum must not be mistaken for the period's full total.
        "total_precipitation_mm": _rounded_or_none(_complete_precipitation_sum(df["precipitation_mm"])),
        "hottest_day": {
            "date": df.loc[hottest_idx, "observation_date"].strftime("%Y-%m-%d"),
            "temp_max_c": float(df.loc[hottest_idx, "temp_max_c"]),
        } if hottest_idx is not None else None,
        "coldest_day": {
            "date": df.loc[coldest_idx, "observation_date"].strftime("%Y-%m-%d"),
            "temp_min_c": float(df.loc[coldest_idx, "temp_min_c"]),
        } if coldest_idx is not None else None,
    }


@router.get("/trends")
def get_trends(
    city: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    granularity: str = Query("monthly", pattern="^(daily|monthly)$"),
    conn=Depends(get_db),
):
    _check_date_range(start, end)
    df = _fetch_daily_df(conn, city, str(start), str(end))
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {city} in {start}..{end}")

    if granularity == "daily":
        out = df[["observation_date", "temp_mean_c", "temp_mean_7d_rolling", "precipitation_mm"]].copy()
        out["period"] = out["observation_date"].dt.strftime("%Y-%m-%d")
        out = out.drop(columns=["observation_date"])
    else:
        df["period"] = df["observation_date"].dt.to_period("M").astype(str)
        out = (
            df.groupby("period")
            .agg(avg_temp_c=("temp_mean_c", "mean"),
                 precipitation_sum_mm=("precipitation_mm", _complete_precipitation_sum))
            .reset_index()
        )
        # Include months for which no observations exist. Without these null
        # rows, the chart misleadingly connects observations a year apart.
        full_months = pd.period_range(
            start=start.strftime("%Y-%m"), end=end.strftime("%Y-%m"), freq="M"
        ).astype(str)
        out = out.set_index("period").reindex(full_months).rename_axis("period").reset_index()
        out["avg_temp_c"] = out["avg_temp_c"].round(2)
        out["precipitation_sum_mm"] = out["precipitation_sum_mm"].round(2)

    # Pandas NaN values cannot safely be serialized as JSON null by default.
    return out.astype(object).where(pd.notna(out), None).to_dict(orient="records")


@router.get("/records")
def get_records(
    city: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    conn=Depends(get_db),
):
    _check_date_range(start, end)
    df = _fetch_daily_df(conn, city, str(start), str(end))
    if df.empty:
        return {"total": 0, "records": []}
    df["observation_date"] = df["observation_date"].dt.strftime("%Y-%m-%d")
    page = df.iloc[offset: offset + limit]
    return {"total": int(len(df)), "records": page.astype(object).where(pd.notna(page), None).to_dict(orient="records")}


@router.get("/data-quality")
def get_data_quality(conn=Depends(get_db)):
    cur = conn.cursor()
    cur.execute(
        """SELECT run_started_at, records_processed, valid_records, duplicates_removed,
                    invalid_records, outliers_flagged, status
           FROM pipeline_runs ORDER BY run_started_at DESC LIMIT 20"""
    )
    cols = ["run_started_at", "records_processed", "valid_records", "duplicates_removed",
            "invalid_records", "outliers_flagged", "status"]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
