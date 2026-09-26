# DataFlow — Interview Prep

Short, honest answers you can defend, tied to actual choices made in this
project.

**ETL vs ELT** — This project is ETL: transform (`transform.py`) happens in
Python before loading into PostgreSQL, because the volume is small enough
that in-process pandas is simpler than pushing raw data in and transforming
with SQL/dbt afterward. At larger scale, ELT (load raw, transform in the
warehouse) is often preferred because it lets you reprocess without
re-fetching from the source, and warehouses parallelize SQL better than a
single Python process.

**Relational modeling** — Two entities: `locations` and `daily_weather`
(fact table with a foreign key to `locations`), plus `pipeline_runs` as an
operational log table, not part of the business model. Kept deliberately
flat — no need to normalize weather codes into a lookup table at this scale.

**Indexing** — Indexes on `observation_date` and `(location_id,
observation_date)` because every analytics query filters or joins on those.
No index on rarely-filtered columns (e.g. `season`) to avoid write overhead
for no read benefit yet.

**Data quality** — Validation flags rows (schema/type/range); cleaning
decides what happens next (dedup, outlier flag, single-field imputation).
Deliberately conservative: never fabricate a missing value across fields
the source didn't provide (see the null `precipitation_sum` case in the
real captured sample used for testing).

**Batch vs streaming** — Batch. Weather changes daily, not per-second;
a daily batch job matches the actual cadence of the source data. Streaming
would add real complexity (windowing, late-arriving data, exactly-once
semantics) with no benefit here.

**Scalability** — Current bottleneck at scale would be row-by-row upserts
in `load.py`. At real scale I'd batch with `COPY`/`execute_values` in
Postgres, or move to a columnar warehouse. Ingestion would also need
concurrency across cities rather than a sequential loop.

**Database performance** — `EXPLAIN ANALYZE` on the trend queries would be
the first tool; the composite index on `(location_id, observation_date)`
is there specifically because every query filters by city and a date range.

**Pipeline failures** — Each city's pipeline run is wrapped in try/except
(`run_pipeline.py`); a failure for one city doesn't stop the others, and
every attempt (success or failure) is recorded in `pipeline_runs` with a
status, so failures are visible, not silent.

**Idempotency** — The core design choice: `UNIQUE(location_id,
observation_date)` plus `ON CONFLICT ... DO UPDATE` means re-running the
pipeline for a date range you've already loaded updates rows instead of
duplicating them. Verified with an automated test that upserts the same
data twice and asserts the row count doesn't change.

**Incremental processing** — Not yet implemented (deliberately deferred
past the MVP). The natural extension: track the last successfully-loaded
date per city and only request `[last_date + 1, today]` from Open-Meteo
instead of re-pulling the full history each run.
