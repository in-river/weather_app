from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib import error, parse, request


def _isoformat_jst(value: datetime) -> str:
    jst = timezone(timedelta(hours=9))
    return value.astimezone(jst).isoformat()


def _safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_openweather_payload(
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
    weather = payload.get("weather") or []
    main = payload.get("main") or {}
    wind = payload.get("wind") or {}
    temperature = _safe_float(main.get("temp"))
    humidity = _safe_float(main.get("humidity"))
    wind_speed = _safe_float(wind.get("speed"))

    precipitation_value = None
    precipitation_unit = "mm"
    precipitation_window_min = 60

    if success:
        precipitation_values: list[float] = []
        precipitation_is_missing = False

        for field_name in ("rain", "snow"):
            if field_name not in payload:
                continue

            precipitation = payload[field_name]
            if not isinstance(precipitation, dict) or "1h" not in precipitation:
                precipitation_is_missing = True
                break

            value = _safe_float(precipitation["1h"])
            if value is None:
                precipitation_is_missing = True
                break
            precipitation_values.append(value)

        if not precipitation_is_missing:
            precipitation_value = sum(precipitation_values, 0.0)

    rain_detected = None
    if precipitation_value is not None:
        rain_detected = 1 if precipitation_value > 0 else 0

    source_time_value = payload.get("dt")
    source_time = None
    if isinstance(source_time_value, (int, float)):
        source_time = datetime.fromtimestamp(source_time_value, tz=timezone.utc)

    normalized = {
        "source": "openweather",
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
        "precipitation_value": precipitation_value,
        "precipitation_unit": precipitation_unit,
        "precipitation_window_min": precipitation_window_min,
        "rain_detected": rain_detected,
        "response_ms": response_ms,
        "success": 1 if success else 0,
        "http_status": http_status,
        "error_type": error_type,
        "raw_json": raw_json,
        "api_version": None,
        "station_id": None,
        "temp_quality": None,
        "humidity_quality": None,
        "wind_quality": None,
        "precip_quality": None,
        "endpoint_sanitized": endpoint_sanitized,
        "collector_version": "1.0.0",
    }

    if weather and isinstance(weather, list) and weather[0]:
        description = weather[0].get("description")
        if description is not None:
            normalized["temp_quality"] = description

    return normalized


def fetch_current_weather(
    *,
    lat: float,
    lon: float,
    api_key: str,
    city: str,
    point_role: str,
    target_time: datetime,
    timeout: float = 10.0,
) -> dict[str, Any]:
    start_time = time.perf_counter()
    endpoint = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&units=metric&appid={api_key}"
    )
    endpoint_sanitized = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&units=metric&appid=[redacted]"
    )
    fetched_at = datetime.now(timezone.utc)
    raw_json = None
    http_status = None
    error_type = None

    try:
        request_obj = request.Request(endpoint, method="GET")
        with request.urlopen(request_obj, timeout=timeout) as response:
            http_status = response.getcode()
            fetched_at = datetime.now(timezone.utc)
            raw_json = response.read().decode("utf-8")
        payload = json.loads(raw_json)
        response_ms = int((time.perf_counter() - start_time) * 1000)
        return _normalize_openweather_payload(
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
        http_status = exc.code
        error_type = "http_error"
        response_ms = int((time.perf_counter() - start_time) * 1000)
        payload = {"cod": exc.code, "message": str(exc)}
        return _normalize_openweather_payload(
            payload,
            city=city,
            point_role=point_role,
            lat=lat,
            lon=lon,
            target_time=target_time,
            fetched_at=datetime.now(timezone.utc),
            response_ms=response_ms,
            http_status=http_status,
            success=False,
            error_type=error_type,
            raw_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            endpoint_sanitized=endpoint_sanitized,
        )
    except (error.URLError, TimeoutError, OSError) as exc:
        error_type = type(exc).__name__
        response_ms = int((time.perf_counter() - start_time) * 1000)
        payload = {"cod": "network_error", "message": str(exc)}
        return _normalize_openweather_payload(
            payload,
            city=city,
            point_role=point_role,
            lat=lat,
            lon=lon,
            target_time=target_time,
            fetched_at=datetime.now(timezone.utc),
            response_ms=response_ms,
            http_status=http_status,
            success=False,
            error_type=error_type,
            raw_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            endpoint_sanitized=endpoint_sanitized,
        )
    except json.JSONDecodeError as exc:
        error_type = "json_decode_error"
        response_ms = int((time.perf_counter() - start_time) * 1000)
        payload = {"cod": "invalid_json", "message": str(exc)}
        return _normalize_openweather_payload(
            payload,
            city=city,
            point_role=point_role,
            lat=lat,
            lon=lon,
            target_time=target_time,
            fetched_at=datetime.now(timezone.utc),
            response_ms=response_ms,
            http_status=http_status,
            success=False,
            error_type=error_type,
            raw_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            endpoint_sanitized=endpoint_sanitized,
        )
