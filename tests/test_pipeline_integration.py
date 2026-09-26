"""
End-to-end test: ingest (offline replay of a real captured snapshot) ->
validate -> clean -> transform -> load, against a throwaway SQLite database.
Exercises the exact same code path pipeline/run_pipeline.py uses.
"""
import os
import tempfile
import unittest

from pipeline import config, ingest, validate, clean, transform, load

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "raw", "lille_2026-09-26_2026-10-10.json"
)


class TestPipelineIntegration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_url = f"sqlite:///{os.path.join(self.tmpdir, 'test.db')}"
        self.conn = load.get_connection(self.db_url)
        load.init_schema(self.conn, self.db_url)

    def tearDown(self):
        self.conn.close()

    def test_full_pipeline_against_real_captured_snapshot(self):
        self.assertTrue(os.path.exists(FIXTURE_PATH), "Real sample fixture missing -- run scripts/build_real_sample_fixture.py")

        payload = ingest.load_raw_snapshot(FIXTURE_PATH)["response"]
        v_result = validate.validate_daily_payload(payload)
        self.assertEqual(v_result.records_processed, 15)
        self.assertEqual(len(v_result.invalid_rows), 0)

        c_result = clean.clean_rows(v_result.valid_rows)
        self.assertEqual(c_result.duplicates_removed, 0)

        df = transform.rows_to_dataframe(c_result.clean_rows, "Lille", "France")
        self.assertEqual(len(df), 15)

        loc = config.LOCATIONS[0]
        location_id = load._get_or_create_location(
            self.conn, loc.city_name, loc.country, loc.latitude, loc.longitude, self.db_url
        )
        written = load.upsert_daily_weather(self.conn, df, location_id, self.db_url)
        self.assertEqual(written, 15)

        # re-run must be idempotent
        written_again = load.upsert_daily_weather(self.conn, df, location_id, self.db_url)
        self.assertEqual(written_again, 15)
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM daily_weather")
        self.assertEqual(cur.fetchone()[0], 15)

        # precipitation_sum was genuinely unavailable from the source and
        # must stay null -- not fabricated as 0 or any other value.
        cur.execute("SELECT COUNT(*) FROM daily_weather WHERE precipitation_mm IS NOT NULL")
        self.assertEqual(cur.fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
