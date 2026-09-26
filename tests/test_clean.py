import unittest
from pipeline.clean import clean_rows, remove_duplicates


class TestClean(unittest.TestCase):
    def test_remove_duplicates(self):
        rows = [{"time": "2026-01-01"}, {"time": "2026-01-01"}, {"time": "2026-01-02"}]
        deduped, removed = remove_duplicates(rows)
        self.assertEqual(len(deduped), 2)
        self.assertEqual(removed, 1)

    def test_outlier_flagged_not_dropped(self):
        rows = [{"time": "2026-01-01", "temperature_2m_max": 50.0, "temperature_2m_min": 40.0,
                  "temperature_2m_mean": 45.0, "precipitation_sum": 0.0}]
        result = clean_rows(rows)
        self.assertEqual(len(result.clean_rows), 1)  # kept, not dropped
        self.assertTrue(result.clean_rows[0]["_outlier"])
        self.assertEqual(result.outliers_flagged, 1)

    def test_impute_single_day_gap(self):
        rows = [
            {"time": "2026-01-01", "temperature_2m_mean": 10.0, "temperature_2m_max": 12,
             "temperature_2m_min": 8, "precipitation_sum": 0.0},
            {"time": "2026-01-02", "temperature_2m_mean": None, "temperature_2m_max": 12,
             "temperature_2m_min": 8, "precipitation_sum": 0.0},
            {"time": "2026-01-03", "temperature_2m_mean": 14.0, "temperature_2m_max": 16,
             "temperature_2m_min": 10, "precipitation_sum": 0.0},
        ]
        result = clean_rows(rows)
        self.assertEqual(result.rows_with_imputed_values, 1)
        self.assertEqual(result.clean_rows[1]["temperature_2m_mean"], 10.0)  # forward-filled
        self.assertTrue(result.clean_rows[1]["_imputed"])
        self.assertFalse(result.clean_rows[0]["_imputed"])

    def test_null_precipitation_not_imputed(self):
        # By design, only temperature_2m_mean is imputed. A null precipitation
        # value should remain null, not be invented as 0.
        rows = [{"time": "2026-01-01", "temperature_2m_mean": 10.0, "temperature_2m_max": 12,
                  "temperature_2m_min": 8, "precipitation_sum": None}]
        result = clean_rows(rows)
        self.assertIsNone(result.clean_rows[0]["precipitation_sum"])


if __name__ == "__main__":
    unittest.main()
