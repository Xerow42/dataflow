import unittest
from pipeline.validate import validate_daily_payload


class TestValidate(unittest.TestCase):
    def test_all_valid_rows(self):
        payload = {"daily": {
            "time": ["2026-01-01", "2026-01-02"],
            "temperature_2m_max": [5.0, 6.0],
            "temperature_2m_min": [1.0, 2.0],
            "temperature_2m_mean": [3.0, 4.0],
            "precipitation_sum": [0.0, 1.2],
            "wind_speed_10m_max": [10.0, 12.0],
            "relative_humidity_2m_mean": [80.0, 82.0],
            "weather_code": [1, 3],
        }}
        result = validate_daily_payload(payload)
        self.assertEqual(result.records_processed, 2)
        self.assertEqual(len(result.valid_rows), 2)
        self.assertEqual(len(result.invalid_rows), 0)

    def test_flags_tmin_greater_than_tmax(self):
        payload = {"daily": {
            "time": ["2026-01-01"],
            "temperature_2m_max": [5.0],
            "temperature_2m_min": [9.0],  # invalid: min > max
            "temperature_2m_mean": [7.0],
            "precipitation_sum": [0.0],
            "wind_speed_10m_max": [10.0],
            "relative_humidity_2m_mean": [80.0],
            "weather_code": [1],
        }}
        result = validate_daily_payload(payload)
        self.assertEqual(len(result.invalid_rows), 1)
        self.assertIn("temperature_2m_min", result.invalid_rows[0]["_errors"][0])

    def test_flags_negative_precipitation(self):
        payload = {"daily": {
            "time": ["2026-01-01"],
            "temperature_2m_max": [5.0], "temperature_2m_min": [1.0],
            "temperature_2m_mean": [3.0], "precipitation_sum": [-2.0],
            "wind_speed_10m_max": [10.0], "relative_humidity_2m_mean": [80.0],
            "weather_code": [1],
        }}
        result = validate_daily_payload(payload)
        self.assertEqual(len(result.invalid_rows), 1)

    def test_flags_invalid_date(self):
        payload = {"daily": {
            "time": ["not-a-date"],
            "temperature_2m_max": [5.0], "temperature_2m_min": [1.0],
            "temperature_2m_mean": [3.0], "precipitation_sum": [0.0],
            "wind_speed_10m_max": [10.0], "relative_humidity_2m_mean": [80.0],
            "weather_code": [1],
        }}
        result = validate_daily_payload(payload)
        self.assertEqual(len(result.invalid_rows), 1)

    def test_null_values_are_allowed(self):
        # None is a legitimate "missing" value at the validation stage;
        # it is handled (imputed or left null) by clean.py, not rejected here.
        payload = {"daily": {
            "time": ["2026-01-01"],
            "temperature_2m_max": [5.0], "temperature_2m_min": [1.0],
            "temperature_2m_mean": [None], "precipitation_sum": [None],
            "wind_speed_10m_max": [10.0], "relative_humidity_2m_mean": [None],
            "weather_code": [1],
        }}
        result = validate_daily_payload(payload)
        self.assertEqual(len(result.valid_rows), 1)


if __name__ == "__main__":
    unittest.main()
