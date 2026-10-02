from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.domain.models import RoadSegment


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass(frozen=True)
class WeatherReading:
    segment_id: str
    precipitation_mm_24h: float
    current_precipitation_mm: float
    precipitation_probability_max: float
    weather_code: int
    observed_at: datetime


@dataclass(frozen=True)
class RouteWeatherPoint:
    precipitation_mm_24h: float
    precipitation_probability_max: float
    elevation_m: float
    observed_at: datetime


class OpenMeteoWeatherService:
    provider = "Open-Meteo"

    @staticmethod
    def _midpoint(road: RoadSegment) -> tuple[float, float]:
        point = road.geometry.coordinates[len(road.geometry.coordinates) // 2]
        return point[1], point[0]

    def fetch_for_segments(self, roads: list[RoadSegment]) -> list[WeatherReading]:
        coordinates = [self._midpoint(road) for road in roads]
        params = {
            "latitude": ",".join(str(latitude) for latitude, _ in coordinates),
            "longitude": ",".join(str(longitude) for _, longitude in coordinates),
            "current": "precipitation,weather_code",
            "hourly": "precipitation,precipitation_probability",
            "forecast_hours": 24,
            "timezone": "auto",
        }
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            response = client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            payload = response.json()

        locations = payload if isinstance(payload, list) else [payload]
        if len(locations) != len(roads):
            raise RuntimeError("Weather provider returned an unexpected number of locations")

        received_at = datetime.now(UTC)
        readings: list[WeatherReading] = []
        for road, location in zip(roads, locations, strict=True):
            hourly = location.get("hourly", {})
            precipitation = [float(value or 0) for value in hourly.get("precipitation", [])[:24]]
            probabilities = [float(value or 0) for value in hourly.get("precipitation_probability", [])[:24]]
            current = location.get("current", {})
            readings.append(WeatherReading(
                segment_id=road.id,
                precipitation_mm_24h=round(sum(precipitation), 1),
                current_precipitation_mm=float(current.get("precipitation") or 0),
                precipitation_probability_max=max(probabilities, default=0),
                weather_code=int(current.get("weather_code") or 0),
                observed_at=received_at,
            ))
        return readings

    def fetch_for_coordinates(self, coordinates: list[list[float]]) -> list[RouteWeatherPoint]:
        params = {
            "latitude": ",".join(str(point[1]) for point in coordinates),
            "longitude": ",".join(str(point[0]) for point in coordinates),
            "hourly": "precipitation,precipitation_probability",
            "forecast_hours": 24,
            "timezone": "auto",
        }
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            payload = response.json()
        locations = payload if isinstance(payload, list) else [payload]
        if len(locations) != len(coordinates):
            raise RuntimeError("Weather provider returned an unexpected number of route samples")
        observed_at = datetime.now(UTC)
        points: list[RouteWeatherPoint] = []
        for location in locations:
            hourly = location.get("hourly", {})
            precipitation = [float(value or 0) for value in hourly.get("precipitation", [])[:24]]
            probabilities = [float(value or 0) for value in hourly.get("precipitation_probability", [])[:24]]
            points.append(RouteWeatherPoint(
                precipitation_mm_24h=round(sum(precipitation), 1),
                precipitation_probability_max=max(probabilities, default=0),
                elevation_m=float(location.get("elevation") or 0),
                observed_at=observed_at,
            ))
        return points


weather_service = OpenMeteoWeatherService()
