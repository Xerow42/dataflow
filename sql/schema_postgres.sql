-- DataFlow -- canonical PostgreSQL schema (used by docker-compose / production).
-- pipeline/load.py applies this automatically on first run when DATABASE_URL
-- points at PostgreSQL. The equivalent SQLite schema (used for local/dev/test
-- runs with zero external services) lives inline in pipeline/load.py.

CREATE TABLE IF NOT EXISTS locations (
    location_id     SERIAL PRIMARY KEY,
    city_name       VARCHAR(100) NOT NULL,
    country         VARCHAR(100) NOT NULL,
    latitude        NUMERIC(8,5) NOT NULL,
    longitude       NUMERIC(8,5) NOT NULL,
    UNIQUE (city_name, country)
);

CREATE TABLE IF NOT EXISTS daily_weather (
    weather_id            SERIAL PRIMARY KEY,
    location_id            INTEGER NOT NULL REFERENCES locations(location_id),
    observation_date        DATE NOT NULL,
    temp_max_c              NUMERIC(5,2),
    temp_min_c              NUMERIC(5,2),
    temp_mean_c             NUMERIC(5,2),
    precipitation_mm        NUMERIC(6,2),
    wind_speed_max_kmh      NUMERIC(5,2),
    humidity_mean_pct       NUMERIC(5,2),
    weather_code            SMALLINT,
    season                  VARCHAR(10),
    is_weekend               BOOLEAN,
    temp_mean_7d_rolling    NUMERIC(5,2),
    is_outlier                BOOLEAN DEFAULT FALSE,
    is_imputed                BOOLEAN DEFAULT FALSE,
    ingested_at               TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (location_id, observation_date)
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id               SERIAL PRIMARY KEY,
    run_started_at        TIMESTAMP NOT NULL,
    run_finished_at        TIMESTAMP,
    records_processed      INTEGER,
    valid_records           INTEGER,
    duplicates_removed      INTEGER,
    invalid_records          INTEGER,
    outliers_flagged         INTEGER,
    status                    VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS idx_daily_weather_date ON daily_weather(observation_date);
CREATE INDEX IF NOT EXISTS idx_daily_weather_loc_date ON daily_weather(location_id, observation_date);
