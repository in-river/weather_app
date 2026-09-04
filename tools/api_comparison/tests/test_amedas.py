from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from tools.api_comparison.collectors.amedas import (
    fetch_current_map,
    normalize_current_weather,
)


API_COMPARISON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_COMPARISON_DIR))
import collect_current  # noqa: E402
from locations import ComparisonPoint  # noqa: E402


class NormalizeAmedasWeatherTest(unittest.TestCase):
    def _normalize(self, station: dict[str, Any]) -> dict[str, Any]:
        fixed_time = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
        return normalize_current_weather(
            map_response={
                "payload": {"43056": station},
                "fetched_at": fixed_time,
                "source_time": datetime(2026, 9, 5, 20, 50, tzinfo=timezone.utc),
                "response_ms": 100,
                "http_status": 200,
                "raw_json": '{"43056":{}}',
                "endpoint_sanitized": "https://www.jma.go.jp/bosai/amedas/data/map/example.json",
            },
            station_id="43056",
            city="kumagaya",
            point_role="primary",
            lat=36.15,
            lon=139.38,
            target_time=fixed_time,
        )

    def test_normal_values_and_quality_are_preserved(self) -> None:
        record = self._normalize(
            {
                "temp": [28.5, 0],
                "humidity": [67, 1],
                "wind": [3.2, 0],
                "precipitation10m": [0.4, 0],
            }
        )

        self.assertEqual(record["source"], "amedas")
        self.assertEqual(record["temperature_c"], 28.5)
        self.assertEqual(record["humidity_pct"], 67.0)
        self.assertEqual(record["wind_speed_ms"], 3.2)
        self.assertEqual(record["precipitation_value"], 0.4)
        self.assertEqual(record["precipitation_window_min"], 10)
        self.assertEqual(record["humidity_quality"], "1")
        self.assertEqual(record["source_time"], "2026-09-06T05:50:00+09:00")

    def test_zero_precipitation_is_preserved(self) -> None:
        record = self._normalize({"precipitation10m": [0, 0]})

        self.assertEqual(record["precipitation_value"], 0.0)
        self.assertEqual(record["rain_detected"], 0)

    def test_missing_values_remain_none(self) -> None:
        record = self._normalize({"temp": [25, 0]})

        self.assertIsNone(record["humidity_pct"])
        self.assertIsNone(record["wind_speed_ms"])
        self.assertIsNone(record["precipitation_value"])
        self.assertIsNone(record["rain_detected"])

    def test_invalid_values_become_none(self) -> None:
        record = self._normalize(
            {
                "temp": ["invalid", 0],
                "humidity": [float("nan"), 0],
                "wind": [{}, 0],
                "precipitation10m": ["invalid", 0],
            }
        )

        self.assertIsNone(record["temperature_c"])
        self.assertIsNone(record["humidity_pct"])
        self.assertIsNone(record["wind_speed_ms"])
        self.assertIsNone(record["precipitation_value"])

    def test_missing_station_returns_empty_success_record(self) -> None:
        record = normalize_current_weather(
            map_response={
                "payload": {},
                "fetched_at": datetime(2026, 9, 5, tzinfo=timezone.utc),
                "source_time": datetime(2026, 9, 5, tzinfo=timezone.utc),
                "response_ms": 100,
                "http_status": 200,
                "raw_json": "{}",
                "endpoint_sanitized": "example",
            },
            station_id="43056",
            city="kumagaya",
            point_role="primary",
            lat=36.15,
            lon=139.38,
            target_time=datetime(2026, 9, 5, tzinfo=timezone.utc),
        )

        self.assertEqual(record["success"], 1)
        self.assertIsNone(record["temperature_c"])
        self.assertIsNone(record["precipitation_value"])
        self.assertEqual(record["raw_json"], "{}")


class FetchAmedasMapFallbackTest(unittest.TestCase):
    TARGET_TIME = datetime(2026, 9, 5, 1, 0, tzinfo=timezone(timedelta(hours=9)))

    @staticmethod
    def _response(raw_json: bytes = b"{}") -> MagicMock:
        response = MagicMock()
        response.getcode.return_value = 200
        response.read.return_value = raw_json
        response.__enter__.return_value = response
        return response

    @staticmethod
    def _latest_time_response(value: bytes = b"2026-09-05T01:00:00+09:00") -> MagicMock:
        return FetchAmedasMapFallbackTest._response(value)

    @staticmethod
    def _not_found() -> HTTPError:
        return HTTPError("https://www.jma.go.jp", 404, "Not Found", {}, None)

    @staticmethod
    def _forbidden() -> HTTPError:
        return HTTPError("https://www.jma.go.jp", 403, "Forbidden", {}, None)

    def test_latest_candidate_succeeds(self) -> None:
        with patch(
            "tools.api_comparison.collectors.amedas.request.urlopen",
            side_effect=[
                self._latest_time_response(),
                self._response(b'{"43056":{}}'),
            ],
        ) as urlopen:
            result = fetch_current_map(target_time=self.TARGET_TIME)

        self.assertEqual(result["source_time"], self.TARGET_TIME)
        self.assertEqual(urlopen.call_count, 2)
        self.assertNotIn("20260905010000", result["endpoint_sanitized"])

    def test_map_url_uses_fourteen_digit_timestamp(self) -> None:
        with patch(
            "tools.api_comparison.collectors.amedas.request.urlopen",
            side_effect=[self._latest_time_response(), self._response()],
        ) as urlopen:
            fetch_current_map(target_time=self.TARGET_TIME)

        map_request = urlopen.call_args_list[1].args[0]
        self.assertTrue(map_request.full_url.endswith("20260905010000.json"))

    def test_older_latest_time_is_used_as_base(self) -> None:
        with patch(
            "tools.api_comparison.collectors.amedas.request.urlopen",
            side_effect=[
                self._latest_time_response(b"2026-09-05T00:50:00+09:00"),
                self._response(),
            ],
        ) as urlopen:
            result = fetch_current_map(target_time=self.TARGET_TIME)

        self.assertEqual(
            result["source_time"],
            datetime(2026, 9, 5, 0, 50, tzinfo=timezone(timedelta(hours=9))),
        )
        self.assertTrue(
            urlopen.call_args_list[1].args[0].full_url.endswith("20260905005000.json")
        )

    def test_newer_latest_time_does_not_exceed_target_time(self) -> None:
        with patch(
            "tools.api_comparison.collectors.amedas.request.urlopen",
            side_effect=[
                self._latest_time_response(b"2026-09-05T01:10:00+09:00"),
                self._response(),
            ],
        ) as urlopen:
            result = fetch_current_map(target_time=self.TARGET_TIME)

        self.assertEqual(result["source_time"], self.TARGET_TIME)
        self.assertTrue(
            urlopen.call_args_list[1].args[0].full_url.endswith("20260905010000.json")
        )

    def test_404_falls_back_by_ten_minutes(self) -> None:
        with patch(
            "tools.api_comparison.collectors.amedas.request.urlopen",
            side_effect=[self._latest_time_response(), self._not_found(), self._response()],
        ) as urlopen:
            result = fetch_current_map(target_time=self.TARGET_TIME)

        self.assertEqual(
            result["source_time"],
            datetime(2026, 9, 5, 0, 50, tzinfo=timezone(timedelta(hours=9))),
        )
        self.assertEqual(urlopen.call_count, 3)

    def test_two_404s_fall_back_by_twenty_minutes(self) -> None:
        with patch(
            "tools.api_comparison.collectors.amedas.request.urlopen",
            side_effect=[
                self._latest_time_response(),
                self._not_found(),
                self._not_found(),
                self._response(),
            ],
        ) as urlopen:
            result = fetch_current_map(target_time=self.TARGET_TIME)

        self.assertEqual(
            result["source_time"],
            datetime(2026, 9, 5, 0, 40, tzinfo=timezone(timedelta(hours=9))),
        )
        self.assertEqual(urlopen.call_count, 4)

    def test_all_candidates_404_raise_after_four_requests(self) -> None:
        with patch(
            "tools.api_comparison.collectors.amedas.request.urlopen",
            side_effect=[self._latest_time_response()]
            + [self._not_found() for _ in range(4)],
        ) as urlopen:
            with self.assertRaises(HTTPError) as raised:
                fetch_current_map(target_time=self.TARGET_TIME)

        self.assertEqual(raised.exception.code, 404)
        self.assertEqual(urlopen.call_count, 5)

    def test_non_404_http_error_does_not_fall_back(self) -> None:
        with patch(
            "tools.api_comparison.collectors.amedas.request.urlopen",
            side_effect=[self._latest_time_response(), self._forbidden()],
        ) as urlopen:
            with self.assertRaises(HTTPError) as raised:
                fetch_current_map(target_time=self.TARGET_TIME)

        self.assertEqual(raised.exception.code, 403)
        self.assertEqual(urlopen.call_count, 2)

    def test_fallback_source_time_is_saved_in_normalized_record(self) -> None:
        fallback_time = datetime(
            2026, 9, 5, 0, 50, tzinfo=timezone(timedelta(hours=9))
        )
        with patch(
            "tools.api_comparison.collectors.amedas.request.urlopen",
            side_effect=[self._latest_time_response(), self._not_found(), self._response()],
        ):
            map_response = fetch_current_map(target_time=self.TARGET_TIME)

        record = normalize_current_weather(
            map_response=map_response,
            station_id="43056",
            city="kumagaya",
            point_role="primary",
            lat=36.15,
            lon=139.38,
            target_time=self.TARGET_TIME,
        )

        self.assertEqual(map_response["source_time"], fallback_time)
        self.assertEqual(record["source_time"], "2026-09-05T00:50:00+09:00")
        self.assertNotEqual(record["source_time"], record["target_time"])

    def test_collection_cycle_fetches_one_map_for_five_cities(self) -> None:
        points = [
            ComparisonPoint(
                city=f"city-{index}",
                point_role="primary",
                lat=35.0,
                lon=139.0,
                station_id=str(index),
            )
            for index in range(5)
        ]
        with patch.object(collect_current, "get_locations", return_value=points), patch.object(
            collect_current, "get_api_key", return_value="key"
        ), patch.object(
            collect_current, "init_database", return_value=Path("test.db")
        ), patch.object(
            collect_current, "fetch_amedas_map", return_value={"payload": {}}
        ) as fetch_map, patch.object(
            collect_current, "_collect_and_save"
        ) as collect_and_save:
            collect_current.main()

        self.assertEqual(fetch_map.call_count, 1)
        amedas_calls = [
            call for call in collect_and_save.call_args_list if call.args[0] == "amedas"
        ]
        self.assertEqual(len(amedas_calls), 5)


if __name__ == "__main__":
    unittest.main()