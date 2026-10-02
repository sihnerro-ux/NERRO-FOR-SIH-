from __future__ import annotations

from datetime import UTC, datetime
from math import asin, cos, radians, sin, sqrt
from typing import TYPE_CHECKING

from app.domain.models import LocationContextResponse
from app.intelligence.model_adapter import model_adapter
from app.routing.geocoding import geocoding_service
from app.weather.open_meteo import weather_service

if TYPE_CHECKING:
    from app.seed.store import SeedStore


def _distance_km(first: list[float], second: list[float]) -> float:
    lon1, lat1 = map(radians, first)
    lon2, lat2 = map(radians, second)
    delta_lon, delta_lat = lon2 - lon1, lat2 - lat1
    value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 6371 * 2 * asin(sqrt(value))


class LocationContextService:
    def assess(self, latitude: float, longitude: float, store: "SeedStore") -> LocationContextResponse:
        if not (21 <= latitude <= 30.5 and 87.5 <= longitude <= 98.5):
            raise ValueError("Selected point is outside the NER operating boundary")
        point = [longitude, latitude]
        warnings: list[str] = []

        nearest_road = min(
            store.roads,
            key=lambda road: min(_distance_km(point, coordinate) for coordinate in road.geometry.coordinates),
        )
        road_distance = min(_distance_km(point, coordinate) for coordinate in nearest_road.geometry.coordinates)
        nearest_facility = min(store.facilities, key=lambda facility: _distance_km(point, facility.location.coordinates))
        facility_distance = _distance_km(point, nearest_facility.location.coordinates)

        fallback_state = nearest_facility.district.split(",")[-1].strip() if "," in nearest_facility.district else None
        fallback_district = nearest_facility.district.split(",")[0].strip()
        location = {
            "label": f"{latitude:.5f}, {longitude:.5f}",
            "state": fallback_state,
            "district": fallback_district,
        }
        try:
            location = geocoding_service.reverse(latitude, longitude)
        except ValueError:
            raise
        except Exception:
            warnings.append("Reverse geocoding unavailable; nearest prototype facility supplied the district context.")

        rainfall = nearest_road.rainfall_mm_24h
        elevation = 300 + nearest_road.slope_degrees * 25
        weather_mode = "CACHED"
        weather_probability = None
        try:
            reading = weather_service.fetch_for_coordinates([point])[0]
            rainfall = reading.precipitation_mm_24h
            elevation = reading.elevation_m
            weather_probability = reading.precipitation_probability_max
            weather_mode = "LIVE"
        except Exception:
            warnings.append("Live weather unavailable; the latest monitored-road weather value is being used.")

        nearby_incidents = [
            incident for incident in store.incidents
            if incident.verification != "REJECTED" and _distance_km(point, incident.location.coordinates) <= 25
        ]
        slope = nearest_road.slope_degrees
        landslide_score = min(100, round(slope * 1.7 + rainfall * 0.35 + len(nearby_incidents) * 8))
        flood_score = min(100, round(rainfall * 0.65 + (15 if elevation < 250 else 0) + len(nearby_incidents) * 5))
        advisory = model_adapter.assess_features(
            distance_km=max(1, road_distance), rainfall_mm=rainfall, slope_deg=slope,
            elevation_m=elevation, incident_count=len(nearby_incidents), road_condition=nearest_road.road_condition,
        )

        return LocationContextResponse(
            latitude=latitude,
            longitude=longitude,
            location_label=str(location["label"]),
            state=location.get("state"),
            district=location.get("district"),
            nearest_road={
                "id": nearest_road.id, "name": nearest_road.road_name,
                "distance_km": round(road_distance, 2), "accessibility": nearest_road.accessibility.value,
                "condition": nearest_road.road_condition, "data_mode": nearest_road.data_mode.value,
            },
            nearest_facility={
                "id": nearest_facility.id, "name": nearest_facility.name,
                "type": nearest_facility.facility_type, "distance_km": round(facility_distance, 2),
                "data_mode": nearest_facility.data_mode.value,
            },
            weather={
                "rainfall_mm_24h": round(rainfall, 1), "precipitation_probability_max": weather_probability,
                "elevation_m": round(elevation), "mode": weather_mode, "provider": "Open-Meteo" if weather_mode == "LIVE" else nearest_road.source,
            },
            predefined_context={
                "slope_degrees": slope, "road_condition": nearest_road.road_condition,
                "landslide_susceptibility": landslide_score, "flood_susceptibility": flood_score,
                "source": "NER prototype monitoring dataset", "mode": "SIMULATED",
            },
            incident_context={
                "nearby_count": len(nearby_incidents), "radius_km": 25,
                "incident_ids": [incident.id for incident in nearby_incidents], "mode": "LIVE_OPERATIONAL_STATE",
            },
            ml_assessment={
                "status": model_adapter.status,
                "model_version": model_adapter.version,
                "risk_probability": round(advisory.probability, 4) if advisory else None,
                "risk_band": advisory.band if advisory else "UNKNOWN",
                "predicted_delay_minutes": round(advisory.delay_minutes) if advisory else None,
                "data_mode": model_adapter.data_mode,
            },
            assessed_at=datetime.now(UTC),
            warnings=warnings,
        )


location_context_service = LocationContextService()
