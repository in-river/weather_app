from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional


def find_project_root(start_path: Optional[Path] = None) -> Path:
    current = (start_path or Path(__file__)).resolve().parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / "pubspec.yaml").exists():
            return candidate
    return current


def load_env_file(env_path: Optional[Path | str] = None) -> Dict[str, str]:
    project_root = find_project_root()
    candidates: list[Path] = []

    if env_path is not None:
        candidates.append(Path(env_path).expanduser())

    candidates.extend(
        [
            project_root / ".env",
            project_root / "tools" / "api_comparison" / ".env",
            Path.cwd() / ".env",
        ]
    )

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            values: Dict[str, str] = {}
            with candidate.open("r", encoding="utf-8") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = [part.strip() for part in line.split("=", 1)]
                    if key:
                        values[key] = value.strip('"\'')
            return values

    return {}


def get_api_key(name: str, env_path: Optional[Path | str] = None) -> Optional[str]:
    env_values = load_env_file(env_path)
    value = env_values.get(name)
    return value if value else None
