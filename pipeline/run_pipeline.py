"""
Orchestrates the full pipeline: ingest -> validate -> clean -> transform -> load.

Usage:
    python -m pipeline.run_pipeline --start 2024-09-01 --end 2025-08-31
    python -m pipeline.run_pipeline --start 2024-09-01 --end 2025-08-31 --offline
        (--offline replays an existing raw snapshot from data/raw/ instead
        of calling the network -- used for the automated tests, and useful
        for CI environments without outbound internet access.)
"""
import argparse
import json
import logging
from datetime import datetime, date, timezone

from . import config, ingest, validate, clean, transform, load

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("dataflow.run_pipeline")


def run_for_location(conn, loc: config.Location, start_date: str, end_date: str, offline: bool) -> dict:
    started_at = datetime.now(timezone.utc).isoformat()
    status = "success"

    try:
        if offline:
            path = ingest._raw_snapshot_path(loc.city_name, start_date, end_date)
            payload = ingest.load_raw_snapshot(path)["response"]
        else:
            payload = ingest.fetch_daily_weather(loc, start_date, end_date)

        v_result = validate.validate_daily_payload(payload)
        c_result = clean.clean_rows(v_result.valid_rows)
        df = transform.rows_to_dataframe(c_result.clean_rows, loc.city_name, loc.country)

        location_id = load._get_or_create_location(
            conn, loc.city_name, loc.country, loc.latitude, loc.longitude
        )
        rows_written = load.upsert_daily_weather(conn, df, location_id) if not df.empty else 0

        summary = {
            "city": loc.city_name,
            "records_processed": v_result.records_processed,
            "valid_records": len(v_result.valid_rows),
            "invalid_records": len(v_result.invalid_rows),
            "duplicates_removed": c_result.duplicates_removed,
            "outliers_flagged": c_result.outliers_flagged,
            "rows_written": rows_written,
            "status": status,
        }

    except Exception as exc:  # noqa: broad -- logged, then re-raised as a summary row
        logger.exception("Pipeline failed for %s", loc.city_name)
        status = "failed"
        summary = {
            "city": loc.city_name,
            "records_processed": 0, "valid_records": 0, "invalid_records": 0,
            "duplicates_removed": 0, "outliers_flagged": 0, "rows_written": 0,
            "status": status, "error": str(exc),
        }

    finished_at = datetime.now(timezone.utc).isoformat()
    load.record_pipeline_run(
        conn, started_at, finished_at,
        summary["records_processed"], summary["valid_records"],
        summary["duplicates_removed"], summary["invalid_records"],
        summary["outliers_flagged"], status,
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run the DataFlow pipeline.")
    today = date.today()
    default_start = today.replace(year=today.year - 1).isoformat()
    parser.add_argument("--start", default=default_start)
    parser.add_argument("--end", default=today.isoformat())
    parser.add_argument("--offline", action="store_true",
                         help="Replay an existing raw snapshot instead of calling the network.")
    args = parser.parse_args()

    conn = load.get_connection()
    load.init_schema(conn)

    summaries = []
    for loc in config.LOCATIONS:
        summaries.append(run_for_location(conn, loc, args.start, args.end, args.offline))

    conn.close()
    print(json.dumps(summaries, indent=2))
    return summaries


if __name__ == "__main__":
    main()
