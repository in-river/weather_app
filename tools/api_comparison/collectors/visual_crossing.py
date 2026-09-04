from __future__ import annotations

import json
import math
import ssl
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib import error, parse, request

try:
    import certifi
except ImportError:
    # Visual Crossing以外のcollectorはcertifi未導入でも利用できるようにする。
    certifi = None


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


def _parse_epoch(value: Any) -> datetime | None:
    epoch = _safe_float(value)
    if epoch is None:
        return None
    try:
        return datetime.fromtimestamp(epoch, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _create_ssl_context() -> ssl.SSLContext:
    if certifi is None:
        raise RuntimeError("certifi is required for Visual Crossing SSL verification")
    return ssl.create_default_context(cafile=certifi.where())


def _sanitize_error_message(value: object, api_key: str) -> str:
    message = str(value)
    return message.replace(api_key, "[redacted]") if api_key else message


def _normalize_visual_crossing_payload(
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
    current_value = payload.get("currentConditions")
    current = current_value if isinstance(current_value, dict) else {}

    temperature = _safe_float(current.get("temp"))
    humidity = _safe_float(current.get("humidity"))
    wind_speed_kmh = _safe_float(current.get("windspeed"))
    wind_speed = wind_speed_kmh / 3.6 if wind_speed_kmh is not None else None
    precipitation = _safe_float(current.get("precip"))

    if not success:
        temperature = None
        humidity = None
        wind_speed = None
        precipitation = None

    rain_detected = None
    if precipitation is not None:
        rain_detected = 1 if precipitation > 0 else 0

    source_time = _parse_epoch(current.get("datetimeEpoch"))

    return {
        "source": "visual_crossing",
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
        # currentConditions.precip の時間窓はAPIレスポンスから確定できないため推測しない。
        "precipitation_window_min": None,
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
    location = parse.quote(f"{lat},{lon}", safe=",")
    base_endpoint = (
        "https://weather.visualcrossing.com/VisualCrossingWebServices/"
        f"rest/services/timeline/{location}"
    )
    parameters = {
        "unitGroup": "metric",
        "include": "current",
        "elements": "datetimeEpoch,temp,humidity,windspeed,precip,conditions",
        "key": api_key,
        "contentType": "json",
    }
    endpoint = base_endpoint + "?" + parse.urlencode(parameters)
    sanitized_parameters = dict(parameters)
    sanitized_parameters["key"] = "[redacted]"
    endpoint_sanitized = base_endpoint + "?" + parse.urlencode(sanitized_parameters)
    http_status = None

    try:
        ssl_context = _create_ssl_context()
        request_obj = request.Request(endpoint, method="GET")
        with request.urlopen(request_obj, timeout=timeout, context=ssl_context) as response:
            http_status = response.getcode()
            fetched_at = datetime.now(timezone.utc)
            raw_json = response.read().decode("utf-8")
        payload = json.loads(raw_json)
        response_ms = int((time.perf_counter() - start_time) * 1000)
        return _normalize_visual_crossing_payload(
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
        payload = {
            "code": exc.code,
            "message": _sanitize_error_message(exc, api_key),
        }
        return _normalize_visual_crossing_payload(
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
    except (error.URLError, TimeoutError, OSError, RuntimeError) as exc:
        payload = {
            "code": "network_error",
            "message": _sanitize_error_message(exc, api_key),
        }
        return _normalize_visual_crossing_payload(
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
        payload = {
            "code": "invalid_json",
            "message": _sanitize_error_message(exc, api_key),
        }
        return _normalize_visual_crossing_payload(
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
