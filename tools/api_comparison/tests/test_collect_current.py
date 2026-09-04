from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


API_COMPARISON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_COMPARISON_DIR))

from collect_current import _floor_target_time  # noqa: E402


class FloorTargetTimeTest(unittest.TestCase):
    def test_five_minutes_is_floored_to_the_hour(self) -> None:
        self.assertEqual(
            _floor_target_time(self._jst_time(17, 5)),
            self._jst_time(17, 0),
        )

    def test_thirty_five_minutes_is_floored_to_half_hour(self) -> None:
        self.assertEqual(
            _floor_target_time(self._jst_time(17, 35)),
            self._jst_time(17, 30),
        )

    def test_exact_half_hour_is_preserved(self) -> None:
        self.assertEqual(
            _floor_target_time(self._jst_time(18, 30, second=45)),
            self._jst_time(18, 30),
        )

    def test_utc_input_is_converted_to_jst_before_flooring(self) -> None:
        utc_time = datetime(2026, 9, 4, 8, 35, tzinfo=timezone.utc)
        self.assertEqual(
            _floor_target_time(utc_time),
            self._jst_time(17, 30),
        )

    @staticmethod
    def _jst_time(hour: int, minute: int, *, second: int = 0) -> datetime:
        return datetime(
            2026,
            9,
            4,
            hour,
            minute,
            second,
            tzinfo=timezone(timedelta(hours=9)),
        )


if __name__ == "__main__":
    unittest.main()
