from __future__ import annotations

import unittest
from datetime import datetime, timezone
from typing import Any

from tools.api_comparison.collectors.open_meteo import (
    _normalize_open_meteo_payload,
)


class NormalizeOpenMeteoPayloadTest(unittest.TestCase):
    def _normalize(self, current: dict[str, Any]) -> dict[str, Any]:
        fixed_time = datetime(2026, 9, 2, tzinfo=timezone.utc)
        return _normalize_open_meteo_payload(
            {"current": current},
            city="kumagaya",
            point_role="primary",
            lat=36.15,
            lon=139.38,
            target_time=fixed_time,
            fetched_at=fixed_time,
            response_ms=100,
            http_status=200,
            success=True,
            error_type=None,
            raw_json="{}",
            endpoint_sanitized="https://api.open-meteo.com/v1/forecast",
        )

    def test_normal_weather_values(self) -> None:
        record = self._normalize(
            {
                "time": "2026-09-02T00:00",
                "interval": 900,
                "temperature_2m": 28.5,
                "relative_humidity_2m": 67,
                "wind_speed_10m": 3.2,
                "precipitation": 0.4,
            }
        )

        self.assertEqual(record["temperature_c"], 28.5)
        self.assertEqual(record["humidity_pct"], 67.0)
        self.assertEqual(record["wind_speed_ms"], 3.2)
        self.assertEqual(record["precipitation_unit"], "mm")
        self.assertEqual(record["source_time"], "2026-09-02T09:00:00+09:00")

    def test_zero_precipitation_is_preserved(self) -> None:
        record = self._normalize({"precipitation": 0, "interval": 900})

        self.assertEqual(record["precipitation_value"], 0.0)
        self.assertEqual(record["rain_detected"], 0)

    def test_positive_precipitation_is_detected(self) -> None:
        record = self._normalize({"precipitation": 1.25, "interval": 900})

        self.assertEqual(record["precipitation_value"], 1.25)
        self.assertEqual(record["rain_detected"], 1)

    def test_missing_precipitation_remains_missing(self) -> None:
        record = self._normalize({"interval": 900})

        self.assertIsNone(record["precipitation_value"])
        self.assertIsNone(record["rain_detected"])

    def test_interval_seconds_are_converted_to_minutes(self) -> None:
        record = self._normalize({"precipitation": 0, "interval": 900})

        self.assertEqual(record["precipitation_window_min"], 15)

    def test_invalid_values_become_none(self) -> None:
        record = self._normalize(
            {
                "time": "invalid",
                "interval": "invalid",
                "temperature_2m": "invalid",
                "relative_humidity_2m": None,
                "wind_speed_10m": float("nan"),
                "precipitation": {},
            }
        )

        self.assertIsNone(record["temperature_c"])
        self.assertIsNone(record["humidity_pct"])
        self.assertIsNone(record["wind_speed_ms"])
        self.assertIsNone(record["precipitation_value"])
        self.assertIsNone(record["precipitation_window_min"])
        self.assertIsNone(record["source_time"])


if __name__ == "__main__":
    unittest.main()
