-- DataFlow -- analytics queries backing the /api/metrics and /api/trends
-- endpoints. Written for PostgreSQL; the FastAPI backend runs equivalent
-- queries in Python for the SQLite dev/test path (see backend/routers/analytics.py).

-- 1. Overall KPIs for a city and date range
SELECT
    COUNT(*)                          AS total_records,
    ROUND(AVG(temp_mean_c)::numeric, 2)   AS avg_temp_c,
    ROUND(SUM(precipitation_mm)::numeric, 2) AS total_precipitation_mm,
    MAX(temp_max_c)                    AS hottest_value_c,
    (SELECT observation_date FROM daily_weather dw2
        WHERE dw2.location_id = dw.location_id
        ORDER BY temp_max_c DESC NULLS LAST LIMIT 1)  AS hottest_day,
    MIN(temp_min_c)                    AS coldest_value_c,
    (SELECT observation_date FROM daily_weather dw3
        WHERE dw3.location_id = dw.location_id
        ORDER BY temp_min_c ASC NULLS LAST LIMIT 1)   AS coldest_day
FROM daily_weather dw
JOIN locations l ON l.location_id = dw.location_id
WHERE l.city_name = :city
  AND observation_date BETWEEN :start_date AND :end_date
GROUP BY dw.location_id;

-- 2. Monthly trend
SELECT
    date_trunc('month', observation_date)::date AS period,
    ROUND(AVG(temp_mean_c)::numeric, 2)  AS avg_temp_c,
    ROUND(SUM(precipitation_mm)::numeric, 2) AS precipitation_sum_mm
FROM daily_weather dw
JOIN locations l ON l.location_id = dw.location_id
WHERE l.city_name = :city
  AND observation_date BETWEEN :start_date AND :end_date
GROUP BY period
ORDER BY period;

-- 3. Daily trend (raw, for charting)
SELECT observation_date, temp_mean_c, temp_mean_7d_rolling, precipitation_mm
FROM daily_weather dw
JOIN locations l ON l.location_id = dw.location_id
WHERE l.city_name = :city
  AND observation_date BETWEEN :start_date AND :end_date
ORDER BY observation_date;

-- 4. Seasonal comparison
SELECT season, ROUND(AVG(temp_mean_c)::numeric, 2) AS avg_temp_c,
       ROUND(SUM(precipitation_mm)::numeric, 2) AS precipitation_sum_mm
FROM daily_weather dw
JOIN locations l ON l.location_id = dw.location_id
WHERE l.city_name = :city
GROUP BY season
ORDER BY avg_temp_c DESC;

-- 5. Ranking: rainiest days on record for a city
SELECT observation_date, precipitation_mm
FROM daily_weather dw
JOIN locations l ON l.location_id = dw.location_id
WHERE l.city_name = :city
ORDER BY precipitation_mm DESC NULLS LAST
LIMIT 10;

-- 6. Simple anomaly view: days flagged as statistical outliers
SELECT observation_date, temp_max_c, temp_min_c, precipitation_mm
FROM daily_weather dw
JOIN locations l ON l.location_id = dw.location_id
WHERE l.city_name = :city AND is_outlier = TRUE
ORDER BY observation_date;

-- 7. Data-quality summary across all pipeline runs
SELECT run_started_at, records_processed, valid_records, duplicates_removed,
       invalid_records, outliers_flagged, status
FROM pipeline_runs
ORDER BY run_started_at DESC
LIMIT 20;
