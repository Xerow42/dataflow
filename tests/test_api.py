"""
API tests using FastAPI's TestClient. These require fastapi to be
installed (pip install -r requirements.txt); they are skipped automatically
if it is not available, which is the case in the sandbox this project was
built in (no outbound network access to install packages -- see README).
"""
import os
import tempfile
import unittest
from datetime import date, timedelta

try:
    import fastapi  # noqa
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi not installed in this environment")
class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        from pipeline import config, ingest, validate, clean, transform, load
        cls.original_database_url = config.DATABASE_URL
        config.DATABASE_URL = f"sqlite:///{os.path.join(cls.tmpdir, 'api_test.db')}"
        conn = load.get_connection()
        load.init_schema(conn)
        loc = config.LOCATIONS[0]
        location_id = load._get_or_create_location(conn, loc.city_name, loc.country, loc.latitude, loc.longitude)

        fixture = os.path.join(os.path.dirname(__file__), "..", "data", "raw",
                                "lille_2026-09-26_2026-10-10.json")
        payload = ingest.load_raw_snapshot(fixture)["response"]
        v = validate.validate_daily_payload(payload)
        c = clean.clean_rows(v.valid_rows)
        df = transform.rows_to_dataframe(c.clean_rows, loc.city_name, loc.country)
        load.upsert_daily_weather(conn, df, location_id)
        conn.close()

        from fastapi.testclient import TestClient
        from backend.main import app
        cls.client = TestClient(app)
        cls.client.__enter__()  # Exercise the lifespan/startup initialization.

    @classmethod
    def tearDownClass(cls):
        from pipeline import config
        cls.client.__exit__(None, None, None)
        config.DATABASE_URL = cls.original_database_url

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)

    def test_categories(self):
        r = self.client.get("/api/categories")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(any(c["city_name"] == "Lille" for c in r.json()))
        self.assertEqual(next(c for c in r.json() if c["city_name"] == "Lille")["end_date"], "2026-10-10")

    def test_metrics(self):
        r = self.client.get("/api/metrics", params={"city": "Lille", "start": "2026-09-26", "end": "2026-10-10"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["records"], 15)
        # This proxy-based fixture has no precipitation readings.
        self.assertIsNone(body["total_precipitation_mm"])

    def test_trends_monthly(self):
        r = self.client.get("/api/trends", params={
            "city": "Lille", "start": "2026-09-26", "end": "2026-10-10", "granularity": "monthly"
        })
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.json()), 1)

    def test_daily_trends_have_chart_period_key(self):
        r = self.client.get("/api/trends", params={
            "city": "Lille", "start": "2026-09-26", "end": "2026-10-10",
            "granularity": "daily",
        })
        self.assertEqual(r.status_code, 200)
        expected = [(date(2026, 9, 26) + timedelta(days=i)).isoformat() for i in range(15)]
        self.assertEqual([row["period"] for row in r.json()], expected)

    def test_monthly_trends_show_missing_month_as_null(self):
        from pipeline import load, transform
        conn = load.get_connection()
        try:
            location_id = load._get_or_create_location(
                conn, "Gapville", "France", 48.0, 2.0
            )
            rows = [{
                "time": day, "temperature_2m_mean": temp,
                "temperature_2m_max": temp + 2, "temperature_2m_min": temp - 2,
                "precipitation_sum": 1.0, "wind_speed_10m_max": 8.0,
                "relative_humidity_2m_mean": 80.0, "weather_code": 1,
            } for day, temp in [("2026-01-01", 3.0), ("2026-03-01", 5.0)]]
            load.upsert_daily_weather(
                conn, transform.rows_to_dataframe(rows, "Gapville", "France"), location_id
            )
        finally:
            conn.close()
        r = self.client.get("/api/trends", params={
            "city": "Gapville", "start": "2026-01-01", "end": "2026-03-31"
        })
        self.assertEqual(r.status_code, 200)
        february = next(month for month in r.json() if month["period"] == "2026-02")
        self.assertIsNone(february["avg_temp_c"])
        self.assertIsNone(february["precipitation_sum_mm"])

        # Requested boundary months must also be represented, even without rows.
        boundaries = self.client.get("/api/trends", params={
            "city": "Gapville", "start": "2025-12-01", "end": "2026-04-30"
        })
        self.assertEqual(boundaries.status_code, 200)
        self.assertEqual([item["period"] for item in boundaries.json()],
                         ["2025-12", "2026-01", "2026-02", "2026-03", "2026-04"])
        self.assertIsNone(boundaries.json()[0]["avg_temp_c"])
        self.assertIsNone(boundaries.json()[-1]["precipitation_sum_mm"])

    def test_partial_precipitation_is_not_reported_as_complete(self):
        from pipeline import load, transform
        conn = load.get_connection()
        try:
            location_id = load._get_or_create_location(conn, "Rainville", "France", 48.0, 2.0)
            rows = [{
                "time": day, "temperature_2m_mean": 4.0,
                "temperature_2m_max": 6.0, "temperature_2m_min": 2.0,
                "precipitation_sum": precip, "wind_speed_10m_max": 8.0,
                "relative_humidity_2m_mean": 80.0, "weather_code": 1,
            } for day, precip in [("2026-02-01", 2.5), ("2026-02-02", None)]]
            load.upsert_daily_weather(conn, transform.rows_to_dataframe(rows, "Rainville", "France"), location_id)
        finally:
            conn.close()
        params = {"city": "Rainville", "start": "2026-02-01", "end": "2026-02-02"}
        metrics = self.client.get("/api/metrics", params=params)
        self.assertEqual(metrics.status_code, 200)
        self.assertIsNone(metrics.json()["total_precipitation_mm"])
        trends = self.client.get("/api/trends", params=params)
        self.assertEqual(trends.status_code, 200)
        self.assertIsNone(trends.json()[0]["precipitation_sum_mm"])
        # Complete one-day range is still a real measured total.
        one_day = self.client.get("/api/metrics", params={**params, "end": "2026-02-01"})
        self.assertEqual(one_day.json()["total_precipitation_mm"], 2.5)

    def test_reversed_date_range_is_rejected(self):
        r = self.client.get("/api/metrics", params={
            "city": "Lille", "start": "2026-10-10", "end": "2026-09-26"
        })
        self.assertEqual(r.status_code, 422)

    def test_records_reject_negative_limit(self):
        r = self.client.get("/api/records", params={
            "city": "Lille", "start": "2026-09-26", "end": "2026-10-10",
            "limit": -1,
        })
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()
