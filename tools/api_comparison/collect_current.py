from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from config import get_api_key
from database import init_database, insert_observation
from locations import get_city_locations
from collectors.open_meteo import fetch_current_weather as fetch_open_meteo
from collectors.openweather import fetch_current_weather as fetch_openweather


def _print_record(record: dict[str, Any], *, save_status: str) -> None:
    print(
        f"source={record['source']} save_status={save_status} "
        f"target_time={record['target_time']} source_time={record['source_time']} "
        f"temperature_c={record['temperature_c']} humidity_pct={record['humidity_pct']} "
        f"wind_speed_ms={record['wind_speed_ms']} "
        f"precipitation_value={record['precipitation_value']} "
        f"precipitation_window_min={record['precipitation_window_min']} "
        f"success={record['success']}"
    )


def _collect_and_save(
    source: str,
    fetch_record: Callable[[], dict[str, Any]],
    db_path: Path,
) -> None:
    try:
        record = fetch_record()
    except Exception as exc:
        # 一方の予期しない取得失敗で、もう一方の収集を止めない。
        print(f"source={source} fetch_failed error_type={type(exc).__name__}: {exc}")
        return

    try:
        insert_observation(db_path, record)
    except Exception as exc:
        _print_record(record, save_status="failed")
        print(f"source={source} save_failed error_type={type(exc).__name__}: {exc}")
        return

    _print_record(record, save_status="saved")


def main() -> None:
    point = next(
        (
            item
            for item in get_city_locations("kumagaya")
            if item.point_role == "primary"
        ),
        None,
    )
    if point is None:
        raise RuntimeError("Kumagaya primary point not found.")

    # 比較キーがずれないよう、実行開始時に一度だけ生成して両APIへ渡す。
    target_time = datetime.now(timezone(timedelta(hours=9))).replace(
        minute=0,
        second=0,
        microsecond=0,
    )
    db_path = init_database()

    api_key = get_api_key("OPENWEATHER_API_KEY")
    if api_key:
        _collect_and_save(
            "openweather",
            lambda: fetch_openweather(
                lat=point.lat,
                lon=point.lon,
                api_key=api_key,
                city=point.city,
                point_role=point.point_role,
                target_time=target_time,
            ),
            db_path,
        )
    else:
        print(
            "source=openweather fetch_failed error_type=missing_api_key: "
            "OPENWEATHER_API_KEY is not set in the local .env file."
        )

    _collect_and_save(
        "open_meteo",
        lambda: fetch_open_meteo(
            lat=point.lat,
            lon=point.lon,
            city=point.city,
            point_role=point.point_role,
            target_time=target_time,
        ),
        db_path,
    )


if __name__ == "__main__":
    main()
