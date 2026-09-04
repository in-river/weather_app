from __future__ import annotations

import json
import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib import error, parse, request


def _isoformat_jst(value: datetime) -> str:
    jst = timezone(timedelta(hours=9))
    return value.astimezone(jst).isoformat()


def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


def _parse_source_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    # APIにはGMTを明示するため、オフセットなしの時刻はUTCとして扱う。
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _interval_minutes(value: Any) -> int | None:
    interval_seconds = _safe_float(value)
    if interval_seconds is None or interval_seconds <= 0:
        return None
    interval_minutes = interval_seconds / 60
    if not interval_minutes.is_integer():
        return None
    return int(interval_minutes)


def _normalize_open_meteo_payload(
    payload: dict[str, Any],
    *,
    city: str,
    point_role: str,
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
) -> dict[str, Any]:
    current_value = payload.get("current")
    current = current_value if isinstance(current_value, dict) else {}

    temperature = _safe_float(current.get("temperature_2m"))
    humidity = _safe_float(current.get("relative_humidity_2m"))
    wind_speed = _safe_float(current.get("wind_speed_10m"))
    precipitation = _safe_float(current.get("precipitation"))
    precipitation_window_min = _interval_minutes(current.get("interval"))

    if not success:
        temperature = None
        humidity = None
        wind_speed = None
        precipitation = None
        precipitation_window_min = None

    rain_detected = None
    if precipitation is not None:
        rain_detected = 1 if precipitation > 0 else 0

    source_time = _parse_source_time(current.get("time"))

    return {
        "source": "open_meteo",
        "city": city,
        "point_role": point_role,
        "lat": float(lat),
        "lon": float(lon),
        "target_time": _isoformat_jst(target_time),
        "fetched_at": _isoformat_jst(fetched_at),
        "source_time": _isoformat_jst(source_time) if source_time is not None else None,
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "wind_speed_ms": wind_speed,
        "precipitation_value": precipitation,
        "precipitation_unit": "mm",
        "precipitation_window_min": precipitation_window_min,
        "rain_detected": rain_detected,
        "response_ms": response_ms,
        "success": 1 if success else 0,
        "http_status": http_status,
        "error_type": error_type,
        "raw_json": raw_json,
        "api_version": "v1",
        "station_id": None,
        "temp_quality": None,
        "humidity_quality": None,
        "wind_quality": None,
        "precip_quality": None,
        "endpoint_sanitized": endpoint_sanitized,
        "collector_version": "1.0.0",
    }


def fetch_current_weather(
    *,
    lat: float,
    lon: float,
    city: str,
    point_role: str,
    target_time: datetime,
    timeout: float = 10.0,
) -> dict[str, Any]:
    start_time = time.perf_counter()
    parameters = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation"
        ),
        "wind_speed_unit": "ms",
        "precipitation_unit": "mm",
        "timezone": "GMT",
    }
    endpoint = "https://api.open-meteo.com/v1/forecast?" + parse.urlencode(parameters)
    endpoint_sanitized = endpoint
    http_status = None

    try:
        request_obj = request.Request(endpoint, method="GET")
        with request.urlopen(request_obj, timeout=timeout) as response:
            http_status = response.getcode()
            fetched_at = datetime.now(timezone.utc)
            raw_json = response.read().decode("utf-8")
        payload = json.loads(raw_json)
        response_ms = int((time.perf_counter() - start_time) * 1000)
        return _normalize_open_meteo_payload(
            payload,
            city=city,
            point_role=point_role,
            lat=lat,
            lon=lon,
            target_time=target_time,
            fetched_at=fetched_at,
            response_ms=response_ms,
            http_status=http_status,
            success=True,
            error_type=None,
            raw_json=raw_json,
            endpoint_sanitized=endpoint_sanitized,
        )
    except error.HTTPError as exc:
        payload = {"code": exc.code, "message": str(exc)}
        return _normalize_open_meteo_payload(
            payload,
            city=city,
            point_role=point_role,
            lat=lat,
            lon=lon,
            target_time=target_time,
            fetched_at=datetime.now(timezone.utc),
            response_ms=int((time.perf_counter() - start_time) * 1000),
            http_status=exc.code,
            success=False,
            error_type="http_error",
            raw_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            endpoint_sanitized=endpoint_sanitized,
        )
    except (error.URLError, TimeoutError, OSError) as exc:
        payload = {"code": "network_error", "message": str(exc)}
        return _normalize_open_meteo_payload(
            payload,
            city=city,
            point_role=point_role,
            lat=lat,
            lon=lon,
            target_time=target_time,
            fetched_at=datetime.now(timezone.utc),
            response_ms=int((time.perf_counter() - start_time) * 1000),
            http_status=http_status,
            success=False,
            error_type=type(exc).__name__,
            raw_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            endpoint_sanitized=endpoint_sanitized,
        )
    except json.JSONDecodeError as exc:
        payload = {"code": "invalid_json", "message": str(exc)}
        return _normalize_open_meteo_payload(
            payload,
            city=city,
            point_role=point_role,
            lat=lat,
            lon=lon,
            target_time=target_time,
            fetched_at=datetime.now(timezone.utc),
            response_ms=int((time.perf_counter() - start_time) * 1000),
            http_status=http_status,
            success=False,
            error_type="json_decode_error",
            raw_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            endpoint_sanitized=endpoint_sanitized,
        )
