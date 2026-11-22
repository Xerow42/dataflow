import unittest
import math
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

    def test_missing_source_arrays_are_invalid(self):
        payload = {"daily": {"time": ["2026-01-01"], "temperature_2m_max": [5.0]}}
        result = validate_daily_payload(payload)
        self.assertEqual(len(result.valid_rows), 0)
        self.assertTrue(any("missing field" in error for error in result.invalid_rows[0]["_errors"]))

    def test_mismatched_array_lengths_are_invalid(self):
        payload = {"daily": {
            "time": ["2026-01-01", "2026-01-02"],
            "temperature_2m_max": [5.0], "temperature_2m_min": [1.0, 2.0],
            "temperature_2m_mean": [3.0, 4.0], "precipitation_sum": [0.0, 0.0],
            "wind_speed_10m_max": [10.0, 11.0],
            "relative_humidity_2m_mean": [80.0, 81.0], "weather_code": [1, 2],
        }}
        result = validate_daily_payload(payload)
        self.assertEqual(len(result.invalid_rows), 2)

    def test_nan_and_invalid_humidity_are_invalid(self):
        valid_payload = {"daily": {
            "time": ["2026-01-01"],
            "temperature_2m_max": [5.0], "temperature_2m_min": [1.0],
            "temperature_2m_mean": [3.0], "precipitation_sum": [0.0],
            "wind_speed_10m_max": [10.0],
            "relative_humidity_2m_mean": [80.0], "weather_code": [1],
        }}
        for field, invalid_value in [
            ("temperature_2m_mean", math.nan),
            ("relative_humidity_2m_mean", 150.0),
            ("temperature_2m_mean", 10 ** 400),
            ("temperature_2m_max", 10 ** 400),
            ("relative_humidity_2m_mean", 10 ** 400),
        ]:
            with self.subTest(field=field, invalid_value=type(invalid_value).__name__):
                payload = {"daily": {key: list(values) for key, values in valid_payload["daily"].items()}}
                payload["daily"][field] = [invalid_value]
                result = validate_daily_payload(payload)
                self.assertEqual(len(result.invalid_rows), 1)
                self.assertTrue(any(field in error or "humidity" in error
                                    for error in result.invalid_rows[0]["_errors"]))

    def test_non_padded_date_is_normalized(self):
        payload = {"daily": {
            "time": ["2026-1-2"],
            "temperature_2m_max": [5.0], "temperature_2m_min": [1.0],
            "temperature_2m_mean": [3.0], "precipitation_sum": [0.0],
            "wind_speed_10m_max": [10.0],
            "relative_humidity_2m_mean": [80.0], "weather_code": [1],
        }}
        result = validate_daily_payload(payload)
        self.assertEqual(result.valid_rows[0]["time"], "2026-01-02")

    def test_invalid_payload_structure_raises(self):
        with self.assertRaises(ValueError):
            validate_daily_payload({"daily": {}})

    def test_empty_time_array_is_not_a_successful_ingestion(self):
        with self.assertRaises(ValueError):
            validate_daily_payload({"daily": {"time": []}})


if __name__ == "__main__":
    unittest.main()
