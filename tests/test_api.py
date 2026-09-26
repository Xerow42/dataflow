"""
API tests using FastAPI's TestClient. These require fastapi to be
installed (pip install -r requirements.txt); they are skipped automatically
if it is not available, which is the case in the sandbox this project was
built in (no outbound network access to install packages -- see README).
"""
import os
import tempfile
import unittest

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
        os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(cls.tmpdir, 'api_test.db')}"

        from pipeline import config, ingest, validate, clean, transform, load
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

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)

    def test_categories(self):
        r = self.client.get("/api/categories")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(any(c["city_name"] == "Lille" for c in r.json()))

    def test_metrics(self):
        r = self.client.get("/api/metrics", params={"city": "Lille", "start": "2026-09-26", "end": "2026-10-10"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["records"], 15)

    def test_trends_monthly(self):
        r = self.client.get("/api/trends", params={
            "city": "Lille", "start": "2026-09-26", "end": "2026-10-10", "granularity": "monthly"
        })
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.json()), 1)


if __name__ == "__main__":
    unittest.main()
