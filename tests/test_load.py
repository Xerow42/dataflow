import os
import tempfile
import unittest

from pipeline import load, transform


class TestLoadSQLite(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_url = f"sqlite:///{os.path.join(self.tmpdir, 'test.db')}"
        self.conn = load.get_connection(self.db_url)
        load.init_schema(self.conn, self.db_url)

    def tearDown(self):
        self.conn.close()

    def _sample_df(self):
        rows = [
            {"time": "2026-01-01", "temperature_2m_max": 5.0, "temperature_2m_min": 1.0,
             "temperature_2m_mean": 3.0, "precipitation_sum": 0.0, "wind_speed_10m_max": 8.0,
             "relative_humidity_2m_mean": 78.0, "weather_code": 1, "_outlier": False, "_imputed": False},
        ]
        return transform.rows_to_dataframe(rows, "Lille", "France")

    def test_get_or_create_location_is_idempotent(self):
        id1 = load._get_or_create_location(self.conn, "Lille", "France", 50.6, 3.0, self.db_url)
        id2 = load._get_or_create_location(self.conn, "Lille", "France", 50.6, 3.0, self.db_url)
        self.assertEqual(id1, id2)
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM locations")
        self.assertEqual(cur.fetchone()[0], 1)

    def test_upsert_is_idempotent_no_duplicates(self):
        loc_id = load._get_or_create_location(self.conn, "Lille", "France", 50.6, 3.0, self.db_url)
        df = self._sample_df()

        written_first = load.upsert_daily_weather(self.conn, df, loc_id, self.db_url)
        written_second = load.upsert_daily_weather(self.conn, df, loc_id, self.db_url)

        self.assertEqual(written_first, 1)
        self.assertEqual(written_second, 1)  # same call count...
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM daily_weather")
        self.assertEqual(cur.fetchone()[0], 1)  # ...but only one row stored (upsert, not insert)

    def test_upsert_updates_existing_row_on_rerun(self):
        loc_id = load._get_or_create_location(self.conn, "Lille", "France", 50.6, 3.0, self.db_url)
        df = self._sample_df()
        load.upsert_daily_weather(self.conn, df, loc_id, self.db_url)

        df2 = df.copy()
        df2.loc[0, "temp_max_c"] = 99.0
        load.upsert_daily_weather(self.conn, df2, loc_id, self.db_url)

        cur = self.conn.cursor()
        cur.execute("SELECT temp_max_c FROM daily_weather WHERE location_id = ?", (loc_id,))
        self.assertEqual(cur.fetchone()[0], 99.0)

    def test_pipeline_run_is_recorded(self):
        load.record_pipeline_run(
            self.conn, "2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z",
            records_processed=1, valid_records=1, duplicates_removed=0,
            invalid_records=0, outliers_flagged=0, status="success",
            database_url=self.db_url,
        )
        cur = self.conn.cursor()
        cur.execute("SELECT status, records_processed FROM pipeline_runs")
        row = cur.fetchone()
        self.assertEqual(row[0], "success")
        self.assertEqual(row[1], 1)


if __name__ == "__main__":
    unittest.main()
