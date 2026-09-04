from __future__ import annotations

import unittest
from datetime import datetime, timezone
from typing import Any

from tools.api_comparison.collectors.tomorrow_io import (
    _normalize_tomorrow_io_payload,
)


class NormalizeTomorrowIoPayloadTest(unittest.TestCase):
    def _normalize(
        self,
        values: dict[str, Any],
        *,
        time_value: Any = "2026-09-04T09:00:00Z",
        success: bool = True,
    ) -> dict[str, Any]:
        fixed_time = datetime(2026, 9, 4, tzinfo=timezone.utc)
        return _normalize_tomorrow_io_payload(
            {"data": {"time": time_value, "values": values}},
            city="kumagaya",
            point_role="primary",
            lat=36.15,
            lon=139.38,
            target_time=fixed_time,
            fetched_at=fixed_time,
            response_ms=100,
            http_status=200 if success else 500,
            success=success,
            error_type=None if success else "http_error",
            raw_json="{}",
            endpoint_sanitized="https://api.tomorrow.io/v4/weather/realtime?location=36.15%2C139.38&units=metric",
        )

    def test_normal_weather_values(self) -> None:
        record = self._normalize(
            {
                "temperature": 28.5,
                "humidity": 67,
                "windSpeed": 3.2,
                "rainIntensity": 0.4,
            }
        )

        self.assertEqual(record["temperature_c"], 28.5)
        self.assertEqual(record["humidity_pct"], 67.0)
        self.assertEqual(record["wind_speed_ms"], 3.2)
        self.assertEqual(record["precipitation_value"], 0.4)
        self.assertEqual(record["precipitation_unit"], "mm/hr")
        self.assertIsNone(record["precipitation_window_min"])
        self.assertEqual(record["source_time"], "2026-09-04T18:00:00+09:00")

    def test_rain_only_is_preserved(self) -> None:
        record = self._normalize({"rainIntensity": 1.25})

        self.assertEqual(record["precipitation_value"], 1.25)
        self.assertEqual(record["rain_detected"], 1)

    def test_all_precipitation_types_are_summed(self) -> None:
        record = self._normalize(
            {
                "rainIntensity": 0.1,
                "snowIntensity": 0.2,
                "sleetIntensity": 0.3,
                "freezingRainIntensity": 0.4,
            }
        )

        self.assertAlmostEqual(record["precipitation_value"], 1.0)
        self.assertEqual(record["rain_detected"], 1)

    def test_zero_precipitation_is_preserved(self) -> None:
        record = self._normalize(
            {
                "rainIntensity": 0,
                "snowIntensity": 0,
                "sleetIntensity": 0,
                "freezingRainIntensity": 0,
            }
        )

        self.assertEqual(record["precipitation_value"], 0.0)
        self.assertEqual(record["rain_detected"], 0)

    def test_missing_precipitation_remains_missing(self) -> None:
        record = self._normalize({})

        self.assertIsNone(record["precipitation_value"])
        self.assertIsNone(record["rain_detected"])

    def test_invalid_values_become_none(self) -> None:
        record = self._normalize(
            {
                "temperature": "invalid",
                "humidity": None,
                "windSpeed": float("nan"),
                "rainIntensity": {},
            },
            time_value="invalid",
        )

        self.assertIsNone(record["temperature_c"])
        self.assertIsNone(record["humidity_pct"])
        self.assertIsNone(record["wind_speed_ms"])
        self.assertIsNone(record["precipitation_value"])
        self.assertIsNone(record["source_time"])

    def test_invalid_precipitation_is_not_treated_as_zero(self) -> None:
        record = self._normalize(
            {
                "rainIntensity": 0.5,
                "snowIntensity": "invalid",
                "sleetIntensity": 0,
                "freezingRainIntensity": 0,
            }
        )

        self.assertIsNone(record["precipitation_value"])
        self.assertIsNone(record["rain_detected"])

    def test_failed_response_clears_weather_values(self) -> None:
        record = self._normalize(
            {
                "temperature": 30,
                "humidity": 50,
                "windSpeed": 3,
                "rainIntensity": 1,
            },
            success=False,
        )

        self.assertIsNone(record["temperature_c"])
        self.assertIsNone(record["humidity_pct"])
        self.assertIsNone(record["wind_speed_ms"])
        self.assertIsNone(record["precipitation_value"])
        self.assertIsNone(record["rain_detected"])


if __name__ == "__main__":
    unittest.main()
