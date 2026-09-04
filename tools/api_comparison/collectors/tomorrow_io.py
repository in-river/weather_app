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
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _sum_precipitation_intensities(values: dict[str, Any]) -> float | None:
    field_names = (
        "rainIntensity",
        "snowIntensity",
        "sleetIntensity",
        "freezingRainIntensity",
    )
    intensities: list[float] = []
    for field_name in field_names:
        raw_value = values.get(field_name)
        if raw_value is None:
            continue
        intensity = _safe_float(raw_value)
        if intensity is None:
            # 存在する不正値を0や欠損項目として扱い、過小評価しない。
            return None
        intensities.append(intensity)
    return sum(intensities) if intensities else None


def _normalize_tomorrow_io_payload(
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
    data_value = payload.get("data")
    data = data_value if isinstance(data_value, dict) else {}
    values_value = data.get("values")
    values = values_value if isinstance(values_value, dict) else {}

    temperature = _safe_float(values.get("temperature"))
    humidity = _safe_float(values.get("humidity"))
    wind_speed = _safe_float(values.get("windSpeed"))
    precipitation_intensity = _sum_precipitation_intensities(values)

    if not success:
        temperature = None
        humidity = None
        wind_speed = None
        precipitation_intensity = None

    rain_detected = None
    if precipitation_intensity is not None:
        rain_detected = 1 if precipitation_intensity > 0 else 0

    source_time = _parse_source_time(data.get("time"))

    return {
        "source": "tomorrow_io",
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
        # Realtime APIが返す降水種別ごとの強度を合計した値(mm/hr)。
        "precipitation_value": precipitation_intensity,
        "precipitation_unit": "mm/hr",
        "precipitation_window_min": None,
        "rain_detected": rain_detected,
        "response_ms": response_ms,
        "success": 1 if success else 0,
        "http_status": http_status,
        "error_type": error_type,
        "raw_json": raw_json,
        "api_version": "v4",
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
    parameters = {
        "location": f"{lat},{lon}",
        "units": "metric",
    }
    endpoint = "https://api.tomorrow.io/v4/weather/realtime?" + parse.urlencode(parameters)
    endpoint_sanitized = endpoint
    http_status = None

    try:
        # APIキーはURLへ含めずヘッダーで送信し、ログやsanitized endpointへの露出を避ける。
        request_obj = request.Request(
            endpoint,
            method="GET",
            headers={"apikey": api_key},
        )
        with request.urlopen(request_obj, timeout=timeout) as response:
            http_status = response.getcode()
            fetched_at = datetime.now(timezone.utc)
            raw_json = response.read().decode("utf-8")
        payload = json.loads(raw_json)
        response_ms = int((time.perf_counter() - start_time) * 1000)
        return _normalize_tomorrow_io_payload(
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
        return _normalize_tomorrow_io_payload(
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
        return _normalize_tomorrow_io_payload(
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
        return _normalize_tomorrow_io_payload(
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
