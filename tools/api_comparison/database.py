from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union


DatabasePath = Union[str, Path]


def get_default_db_path() -> Path:
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "weather_validation.db"


def init_database(db_path: DatabasePath | None = None) -> Path:
    resolved_path = Path(db_path) if db_path is not None else get_default_db_path()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(resolved_path)
    try:
        connection.execute("PRAGMA journal_mode = WAL;")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_time TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                source_time TEXT,
                source TEXT NOT NULL,
                api_version TEXT,
                city TEXT NOT NULL,
                point_role TEXT NOT NULL,
                station_id TEXT,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                temperature_c REAL,
                humidity_pct REAL,
                wind_speed_ms REAL,
                precipitation_value REAL,
                precipitation_unit TEXT,
                precipitation_window_min INTEGER,
                rain_detected INTEGER,
                temp_quality TEXT,
                humidity_quality TEXT,
                wind_quality TEXT,
                precip_quality TEXT,
                http_status INTEGER,
                response_ms INTEGER,
                success INTEGER NOT NULL,
                error_type TEXT,
                endpoint_sanitized TEXT,
                raw_json TEXT,
                collector_version TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_observations_source_city_role_time
            ON observations (source, city, point_role, target_time)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_observations_target_time
            ON observations (target_time)
            """
        )
        connection.commit()
    finally:
        connection.close()

    return resolved_path
