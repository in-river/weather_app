from __future__ import annotations

import unittest
from datetime import datetime, timezone
from typing import Any

from tools.api_comparison.collectors.openweather import (
    _normalize_openweather_payload,
)


class NormalizeOpenWeatherPrecipitationTest(unittest.TestCase):
    def _normalize(
        self,
        payload: dict[str, Any],
        *,
        success: bool = True,
    ) -> dict[str, Any]:
        fixed_time = datetime(2026, 9, 2, tzinfo=timezone.utc)
        return _normalize_openweather_payload(
            payload,
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
            endpoint_sanitized="https://example.invalid/weather?appid=[redacted]",
        )

    def assert_precipitation(
        self,
        payload: dict[str, Any],
        expected_value: float | None,
        expected_detected: int | None,
        *,
        success: bool = True,
    ) -> None:
        record = self._normalize(payload, success=success)
        self.assertEqual(record["precipitation_value"], expected_value)
        self.assertEqual(record["rain_detected"], expected_detected)

    def test_rain_and_snow_are_absent(self) -> None:
        self.assert_precipitation({}, 0.0, 0)

    def test_only_rain_is_present(self) -> None:
        self.assert_precipitation({"rain": {"1h": 1.25}}, 1.25, 1)

    def test_only_snow_is_present(self) -> None:
        self.assert_precipitation({"snow": {"1h": 2.5}}, 2.5, 1)

    def test_rain_and_snow_are_added(self) -> None:
        self.assert_precipitation(
            {"rain": {"1h": 0.75}, "snow": {"1h": 1.5}},
            2.25,
            1,
        )

    def test_observed_zero_is_preserved(self) -> None:
        self.assert_precipitation({"rain": {"1h": 0}}, 0.0, 0)

    def test_missing_one_hour_value_is_missing(self) -> None:
        self.assert_precipitation({"rain": {}}, None, None)

    def test_invalid_precipitation_is_missing(self) -> None:
        self.assert_precipitation({"rain": {"1h": "invalid"}}, None, None)

    def test_error_response_is_missing(self) -> None:
        self.assert_precipitation(
            {"rain": {"1h": 1.0}},
            None,
            None,
            success=False,
        )


if __name__ == "__main__":
    unittest.main()
