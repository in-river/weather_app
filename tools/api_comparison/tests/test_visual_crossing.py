from __future__ import annotations

import unittest
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

from tools.api_comparison.collectors.visual_crossing import (
    fetch_current_weather,
    _normalize_visual_crossing_payload,
)


class NormalizeVisualCrossingPayloadTest(unittest.TestCase):
    def _normalize(
        self,
        current: dict[str, Any],
        *,
        success: bool = True,
    ) -> dict[str, Any]:
        fixed_time = datetime(2026, 9, 4, tzinfo=timezone.utc)
        return _normalize_visual_crossing_payload(
            {"currentConditions": current},
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
            endpoint_sanitized="https://weather.visualcrossing.com/example?key=%5Bredacted%5D",
        )

    def test_normal_weather_values(self) -> None:
        record = self._normalize(
            {
                "datetimeEpoch": 1788480000,
                "temp": 28.5,
                "humidity": 67,
                "windspeed": 10.8,
                "precip": 0.4,
            }
        )

        self.assertEqual(record["temperature_c"], 28.5)
        self.assertEqual(record["humidity_pct"], 67.0)
        self.assertAlmostEqual(record["wind_speed_ms"], 3.0)
        self.assertEqual(record["precipitation_value"], 0.4)
        self.assertEqual(record["precipitation_unit"], "mm")
        self.assertIsNone(record["precipitation_window_min"])
        self.assertIsNotNone(record["source_time"])

    def test_zero_precipitation_is_preserved(self) -> None:
        record = self._normalize({"precip": 0})

        self.assertEqual(record["precipitation_value"], 0.0)
        self.assertEqual(record["rain_detected"], 0)

    def test_positive_precipitation_is_detected(self) -> None:
        record = self._normalize({"precip": 1.25})

        self.assertEqual(record["precipitation_value"], 1.25)
        self.assertEqual(record["rain_detected"], 1)

    def test_missing_precipitation_remains_missing(self) -> None:
        record = self._normalize({})

        self.assertIsNone(record["precipitation_value"])
        self.assertIsNone(record["rain_detected"])

    def test_invalid_values_become_none(self) -> None:
        record = self._normalize(
            {
                "datetimeEpoch": "invalid",
                "temp": "invalid",
                "humidity": None,
                "windspeed": float("nan"),
                "precip": {},
            }
        )

        self.assertIsNone(record["temperature_c"])
        self.assertIsNone(record["humidity_pct"])
        self.assertIsNone(record["wind_speed_ms"])
        self.assertIsNone(record["precipitation_value"])
        self.assertIsNone(record["source_time"])

    def test_failed_response_clears_weather_values(self) -> None:
        record = self._normalize(
            {"temp": 30, "humidity": 50, "windspeed": 7.2, "precip": 1},
            success=False,
        )

        self.assertIsNone(record["temperature_c"])
        self.assertIsNone(record["humidity_pct"])
        self.assertIsNone(record["wind_speed_ms"])
        self.assertIsNone(record["precipitation_value"])
        self.assertIsNone(record["rain_detected"])


class FetchVisualCrossingWeatherTest(unittest.TestCase):
    @patch("tools.api_comparison.collectors.visual_crossing.request.urlopen")
    @patch("tools.api_comparison.collectors.visual_crossing.ssl.create_default_context")
    @patch("tools.api_comparison.collectors.visual_crossing.certifi")
    def test_uses_certifi_ssl_context_without_exposing_api_key(
        self,
        mock_certifi: MagicMock,
        mock_create_default_context: MagicMock,
        mock_urlopen: MagicMock,
    ) -> None:
        mock_certifi.where.return_value = "certifi-ca.pem"
        ssl_context = MagicMock()
        mock_create_default_context.return_value = ssl_context
        response = MagicMock()
        response.getcode.return_value = 200
        response.read.return_value = b'{"currentConditions":{"precip":0}}'
        mock_urlopen.return_value.__enter__.return_value = response
        api_key = "secret-api-key"

        record = fetch_current_weather(
            lat=36.15,
            lon=139.38,
            api_key=api_key,
            city="kumagaya",
            point_role="primary",
            target_time=datetime(2026, 9, 4, tzinfo=timezone.utc),
        )

        mock_create_default_context.assert_called_once_with(cafile="certifi-ca.pem")
        self.assertIs(mock_urlopen.call_args.kwargs["context"], ssl_context)
        self.assertNotIn(api_key, record["endpoint_sanitized"])
        self.assertIn("%5Bredacted%5D", record["endpoint_sanitized"])

    @patch("tools.api_comparison.collectors.visual_crossing.certifi", None)
    def test_missing_certifi_returns_failure_record(self) -> None:
        api_key = "secret-api-key"

        record = fetch_current_weather(
            lat=36.15,
            lon=139.38,
            api_key=api_key,
            city="kumagaya",
            point_role="primary",
            target_time=datetime(2026, 9, 4, tzinfo=timezone.utc),
        )

        self.assertEqual(record["success"], 0)
        self.assertEqual(record["error_type"], "RuntimeError")
        self.assertNotIn(api_key, record["endpoint_sanitized"])
        self.assertNotIn(api_key, record["raw_json"])

if __name__ == "__main__":
    unittest.main()
