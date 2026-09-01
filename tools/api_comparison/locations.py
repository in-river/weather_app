from __future__ import annotations

from dataclasses import dataclass
from typing import Final, List


@dataclass(frozen=True)
class ComparisonPoint:
    city: str
    point_role: str
    lat: float
    lon: float
    station_id: str | None = None
    description: str | None = None


AMEDAS_POINTS: Final[List[ComparisonPoint]] = [
    ComparisonPoint(
        city="kumagaya",
        point_role="primary",
        lat=36.150000,
        lon=139.380000,
        station_id="43056",
        description="熊谷 アメダス観測地点",
    ),
    ComparisonPoint(
        city="tokyo",
        point_role="primary",
        lat=35.691667,
        lon=139.750000,
        station_id="44132",
        description="東京 アメダス観測地点",
    ),
    ComparisonPoint(
        city="tokyo",
        point_role="wind",
        lat=35.691667,
        lon=139.751667,
        station_id="44132",
        description="東京 風観測用座標",
    ),
    ComparisonPoint(
        city="shizuoka",
        point_role="primary",
        lat=34.975000,
        lon=138.403333,
        station_id="50331",
        description="静岡 アメダス観測地点",
    ),
    ComparisonPoint(
        city="osaka",
        point_role="primary",
        lat=34.681667,
        lon=135.518333,
        station_id="62078",
        description="大阪 アメダス観測地点",
    ),
    ComparisonPoint(
        city="osaka",
        point_role="wind",
        lat=34.675000,
        lon=135.546667,
        station_id="62078",
        description="大阪 風観測用座標",
    ),
    ComparisonPoint(
        city="matsuyama",
        point_role="primary",
        lat=33.843333,
        lon=132.776667,
        station_id="73166",
        description="松山 アメダス観測地点",
    ),
    ComparisonPoint(
        city="matsuyama",
        point_role="wind",
        lat=33.835000,
        lon=132.793333,
        station_id="73166",
        description="松山 風観測用座標",
    ),
]


def get_locations() -> List[ComparisonPoint]:
    return list(AMEDAS_POINTS)


def get_city_locations(city: str) -> List[ComparisonPoint]:
    return [point for point in AMEDAS_POINTS if point.city == city]
