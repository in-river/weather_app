from __future__ import annotations

from datetime import datetime, timedelta, timezone

from config import get_api_key
from database import init_database, insert_observation
from locations import get_city_locations
from collectors.openweather import fetch_current_weather


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

    api_key = get_api_key("OPENWEATHER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENWEATHER_API_KEY is not set in the local .env file.")

    target_time = datetime.now(timezone(timedelta(hours=9))).replace(
        minute=0,
        second=0,
        microsecond=0,
    )
    record = fetch_current_weather(
        lat=point.lat,
        lon=point.lon,
        api_key=api_key,
        city=point.city,
        point_role=point.point_role,
        target_time=target_time,
    )

    db_path = init_database()
    insert_observation(db_path, record)

    print(
        f"saved: city={record['city']} point_role={record['point_role']} "
        f"target_time={record['target_time']} fetched_at={record['fetched_at']} "
        f"source_time={record['source_time']} "
        f"temperature_c={record['temperature_c']} humidity_pct={record['humidity_pct']} "
        f"wind_speed_ms={record['wind_speed_ms']} success={record['success']}"
    )


if __name__ == "__main__":
    main()
