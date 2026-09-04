from __future__ import annotations

import json
import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib import error, request


JST = timezone(timedelta(hours=9))
AMEDAS_MAP_URL = "https://www.jma.go.jp/bosai/amedas/data/map/{timestamp}.json"
AMEDAS_MAP_ENDPOINT_SANITIZED = AMEDAS_MAP_URL.format(timestamp="[timestamp]")
AMEDAS_LATEST_TIME_URL = "https://www.jma.go.jp/bosai/amedas/data/latest_time.txt"
MAX_MAP_CANDIDATES = 4


def _isoformat_jst(value: datetime) -> str:
    return value.astimezone(JST).isoformat()


def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


def _observation_time(now: datetime) -> datetime:
    current = now.astimezone(JST)
    minute = current.minute - current.minute % 10
    return current.replace(minute=minute, second=0, microsecond=0)


def _map_candidates(target_time: datetime) -> list[datetime]:
    return [
        target_time - timedelta(minutes=10 * offset)
        for offset in range(MAX_MAP_CANDIDATES)
    ]


def _parse_latest_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=JST)
    return parsed.astimezone(JST)


def _value_and_quality(value: Any) -> tuple[float | None, str | None]:
    if not isinstance(value, (list, tuple)) or not value:
        return None, None
    normalized = _safe_float(value[0])
    quality = str(value[1]) if len(value) > 1 and value[1] is not None else None
    return normalized, quality


def _station_record(
    station: dict[str, Any] | None,
    *,
    city: str,
    point_role: str,
    station_id: str,
    lat: float,
    lon: float,
    target_time: datetime,
    fetched_at: datetime,
    response_ms: int,
    http_status: int | None,
    success: bool,
    error_type: str | None,
    raw_json: str,
    endpoint_sanitized: str,
    source_time: datetime | None,
) -> dict[str, Any]:
    station = station if isinstance(station, dict) else {}
    temperature, temp_quality = _value_and_quality(station.get("temp"))
    humidity, humidity_quality = _value_and_quality(station.get("humidity"))
    wind_speed, wind_quality = _value_and_quality(station.get("wind"))
    precipitation, precip_quality = _value_and_quality(
        station.get("precipitation10m")
    )

    if not success:
        temperature = humidity = wind_speed = precipitation = None
        temp_quality = humidity_quality = wind_quality = precip_quality = None

    rain_detected = None
    if precipitation is not None:
        rain_detected = 1 if precipitation > 0 else 0

    return {
        "source": "amedas",
        "city": city,
        "point_role": point_role,
        "lat": float(lat),
        "lon": float(lon),
        "target_time": _isoformat_jst(target_time),
        "fetched_at": _isoformat_jst(fetched_at),
        "source_time": _isoformat_jst(source_time) if source_time else None,
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "wind_speed_ms": wind_speed,
        "precipitation_value": precipitation,
        "precipitation_unit": "mm",
        "precipitation_window_min": 10,
        "rain_detected": rain_detected,
        "response_ms": response_ms,
        "success": 1 if success else 0,
        "http_status": http_status,
        "error_type": error_type,
        "raw_json": raw_json,
        "api_version": "map",
        "station_id": station_id,
        "temp_quality": temp_quality,
        "humidity_quality": humidity_quality,
        "wind_quality": wind_quality,
        "precip_quality": precip_quality,
        "endpoint_sanitized": endpoint_sanitized,
        "collector_version": "1.0.0",
    }


def normalize_current_weather(
    *,
    map_response: dict[str, Any],
    station_id: str,
    city: str,
    point_role: str,
    lat: float,
    lon: float,
    target_time: datetime,
) -> dict[str, Any]:
    payload = map_response.get("payload")
    stations = payload if isinstance(payload, dict) else {}
    station = stations.get(station_id)
    return _station_record(
        station if isinstance(station, dict) else None,
        city=city,
        point_role=point_role,
        station_id=station_id,
        lat=lat,
        lon=lon,
        target_time=target_time,
        fetched_at=map_response["fetched_at"],
        response_ms=map_response["response_ms"],
        http_status=map_response["http_status"],
        success=True,
        error_type=None,
        raw_json=map_response["raw_json"],
        endpoint_sanitized=map_response["endpoint_sanitized"],
        source_time=map_response.get("source_time"),
    )


def fetch_current_map(
    *,
    target_time: datetime,
    timeout: float = 10.0,
) -> dict[str, Any]:
    start_time = time.perf_counter()
    latest_time_request = request.Request(AMEDAS_LATEST_TIME_URL, method="GET")
    with request.urlopen(latest_time_request, timeout=timeout) as response:
        latest_time = _parse_latest_time(response.read().decode("utf-8"))
    base_time = _observation_time(min(target_time.astimezone(JST), latest_time))
    last_not_found: error.HTTPError | None = None

    for observation_time in _map_candidates(base_time):
        timestamp = observation_time.strftime("%Y%m%d%H%M%S")
        endpoint = AMEDAS_MAP_URL.format(timestamp=timestamp)
        request_obj = request.Request(endpoint, method="GET")
        try:
            with request.urlopen(request_obj, timeout=timeout) as response:
                http_status = response.getcode()
                fetched_at = datetime.now(timezone.utc)
                raw_json = response.read().decode("utf-8")
            return {
                "payload": json.loads(raw_json),
                "source_time": observation_time,
                "fetched_at": fetched_at,
                "response_ms": int((time.perf_counter() - start_time) * 1000),
                "http_status": http_status,
                "raw_json": raw_json,
                "endpoint_sanitized": AMEDAS_MAP_ENDPOINT_SANITIZED,
            }
        except error.HTTPError as exc:
            if exc.code != 404:
                raise
            last_not_found = exc

    if last_not_found is not None:
        raise last_not_found
    raise RuntimeError("AMeDAS map candidates are empty")


def failure_from_fetch_error(
    *,
    exc: Exception,
    station_id: str,
    city: str,
    point_role: str,
    lat: float,
    lon: float,
    target_time: datetime,
) -> dict[str, Any]:
    raw_json = json.dumps(
        {"code": "fetch_error", "message": str(exc)},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return _station_record(
        None,
        city=city,
        point_role=point_role,
        station_id=station_id,
        lat=lat,
        lon=lon,
        target_time=target_time,
        fetched_at=datetime.now(timezone.utc),
        response_ms=0,
        http_status=None,
        success=False,
        error_type=type(exc).__name__,
        raw_json=raw_json,
        endpoint_sanitized=AMEDAS_MAP_ENDPOINT_SANITIZED,
        source_time=None,
    )


def fetch_current_weather(
    *,
    station_id: str,
    lat: float,
    lon: float,
    city: str,
    point_role: str,
    target_time: datetime,
    timeout: float = 10.0,
) -> dict[str, Any]:
    try:
        return normalize_current_weather(
            map_response=fetch_current_map(target_time=target_time, timeout=timeout),
            station_id=station_id,
            city=city,
            point_role=point_role,
            lat=lat,
            lon=lon,
            target_time=target_time,
        )
    except Exception as exc:
        return failure_from_fetch_error(
            exc=exc,
            station_id=station_id,
            city=city,
            point_role=point_role,
            lat=lat,
            lon=lon,
            target_time=target_time,
        )