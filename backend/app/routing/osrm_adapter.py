from __future__ import annotations

from dataclasses import dataclass
import os

import httpx


@dataclass(frozen=True)
class OsrmRoute:
    distance_m: float
    duration_seconds: float
    coordinates: list[list[float]]
    road_names: list[str]


class OsrmRoutingAdapter:
    provider = "OSRM / OpenStreetMap"

    def __init__(self) -> None:
        self.base_url = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")

    def fetch_routes(self, source: list[float], destination: list[float]) -> list[OsrmRoute]:
        coordinates = f"{source[0]},{source[1]};{destination[0]},{destination[1]}"
        params = {
            "alternatives": 3,
            "steps": "true",
            "geometries": "geojson",
            "overview": "full",
        }
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            response = client.get(f"{self.base_url}/route/v1/driving/{coordinates}", params=params)
            response.raise_for_status()
            payload = response.json()
        if payload.get("code") != "Ok":
            raise RuntimeError(f"OSRM route request failed with code {payload.get('code', 'UNKNOWN')}")

        routes: list[OsrmRoute] = []
        for item in payload.get("routes", []):
            geometry = item.get("geometry", {})
            route_coordinates = geometry.get("coordinates", [])
            if len(route_coordinates) < 2:
                continue
            names: list[str] = []
            for leg in item.get("legs", []):
                for step in leg.get("steps", []):
                    name = str(step.get("name") or "").strip()
                    if name and (not names or names[-1] != name):
                        names.append(name)
            routes.append(OsrmRoute(
                distance_m=float(item["distance"]),
                duration_seconds=float(item["duration"]),
                coordinates=[[float(point[0]), float(point[1])] for point in route_coordinates],
                road_names=names,
            ))
        if not routes:
            raise RuntimeError("OSRM returned no usable route geometry")
        return routes


osrm_adapter = OsrmRoutingAdapter()
