import unittest
from pipeline.transform import rows_to_dataframe


class TestTransform(unittest.TestCase):
    def _sample_rows(self):
        return [
            {"time": "2026-01-03", "temperature_2m_max": 6.0, "temperature_2m_min": 2.0,
             "temperature_2m_mean": 4.0, "precipitation_sum": 1.0, "wind_speed_10m_max": 10.0,
             "relative_humidity_2m_mean": 80.0, "weather_code": 3, "_outlier": False, "_imputed": False},
            {"time": "2026-01-01", "temperature_2m_max": 5.0, "temperature_2m_min": 1.0,
             "temperature_2m_mean": 3.0, "precipitation_sum": 0.0, "wind_speed_10m_max": 8.0,
             "relative_humidity_2m_mean": 78.0, "weather_code": 1, "_outlier": False, "_imputed": False},
        ]

    def test_columns_renamed_and_sorted_by_date(self):
        df = rows_to_dataframe(self._sample_rows(), "Lille", "France")
        self.assertListEqual(
            list(df["observation_date"].dt.strftime("%Y-%m-%d")), ["2026-01-01", "2026-01-03"]
        )
        self.assertIn("temp_max_c", df.columns)
        self.assertIn("temp_mean_7d_rolling", df.columns)

    def test_season_derivation(self):
        df = rows_to_dataframe(self._sample_rows(), "Lille", "France")
        self.assertTrue((df["season"] == "winter").all())

    def test_empty_input_returns_empty_dataframe(self):
        df = rows_to_dataframe([], "Lille", "France")
        self.assertTrue(df.empty)

    def test_rolling_mean_is_cumulative_average_within_window(self):
        df = rows_to_dataframe(self._sample_rows(), "Lille", "France")
        # 2 points only -> rolling(7, min_periods=1) == running mean
        self.assertAlmostEqual(df.iloc[0]["temp_mean_7d_rolling"], 3.0)
        self.assertAlmostEqual(df.iloc[1]["temp_mean_7d_rolling"], 3.5)


if __name__ == "__main__":
    unittest.main()
