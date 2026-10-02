from __future__ import annotations

from datetime import UTC, datetime
from math import asin, atan, ceil, cos, degrees, radians, sin, sqrt
import logging

from app.domain.models import DataMode, GeoJsonLineString, Incident, RoadAccessibility, RoadSegment, RouteCandidate, RouteIntelligenceSegment, RoutePlanRequest, RoutePlanResponse, RoutePreference, RouteProcessingStep
from app.intelligence.model_adapter import model_adapter
from app.routing.engine import RoutingEngine
from app.routing.osrm_adapter import OsrmRoute, osrm_adapter
from app.weather.open_meteo import RouteWeatherPoint, weather_service


logger = logging.getLogger(__name__)

FACILITY_COORDINATES = {
    "FAC-GHY-MED": [91.7362, 26.1445],
    "FAC-TEZ-HUB": [92.7926, 26.6528],
    "FAC-BOM-RELIEF": [92.412, 27.264],
    "FAC-TAW-HOSP": [91.865, 27.586],
}

FACILITY_LABELS = {
    "FAC-GHY-MED": "Guwahati",
    "FAC-TEZ-HUB": "Tezpur",
    "FAC-BOM-RELIEF": "Bomdila",
    "FAC-TAW-HOSP": "Tawang",
}


def _haversine_km(first: list[float], second: list[float]) -> float:
    lon1, lat1 = map(radians, first)
    lon2, lat2 = map(radians, second)
    delta_lon = lon2 - lon1
    delta_lat = lat2 - lat1
    value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(value))


def _simplify(coordinates: list[list[float]], maximum_points: int = 1200) -> list[list[float]]:
    if len(coordinates) <= maximum_points:
        return coordinates
    step = max(1, ceil((len(coordinates) - 1) / (maximum_points - 1)))
    reduced = coordinates[::step]
    if reduced[-1] != coordinates[-1]:
        reduced.append(coordinates[-1])
    return reduced


class RoutePlanningService:
    def __init__(self) -> None:
        self.external = osrm_adapter
        self.weather = weather_service

    @staticmethod
    def _matched_segments(route: OsrmRoute, roads: list[RoadSegment]) -> list[RoadSegment]:
        sample_step = max(1, len(route.coordinates) // 2500)
        route_points = route.coordinates[::sample_step]
        matched: list[RoadSegment] = []
        for road in roads:
            close_points = 0
            for road_point in road.geometry.coordinates:
                if min(_haversine_km(road_point, route_point) for route_point in route_points) <= 12:
                    close_points += 1
            if close_points >= min(2, len(road.geometry.coordinates)):
                matched.append(road)
        return matched

    @staticmethod
    def _sample_coordinates(route: OsrmRoute, count: int = 8) -> list[list[float]]:
        if count <= 1:
            return route.coordinates[:1]
        if len(route.coordinates) <= count:
            return route.coordinates
        return [route.coordinates[round(index * (len(route.coordinates) - 1) / (count - 1))] for index in range(count)]

    @staticmethod
    def _nearby_incident_count(route: OsrmRoute, incidents: list[Incident]) -> int:
        sample_step = max(1, len(route.coordinates) // 1500)
        route_points = route.coordinates[::sample_step]
        return sum(
            incident.verification != "REJECTED"
            and min(_haversine_km(incident.location.coordinates, point) for point in route_points) <= 12
            for incident in incidents
        )

    @staticmethod
    def _route_sections(coordinates: list[list[float]], count: int) -> list[list[list[float]]]:
        if len(coordinates) < 2:
            return []
        segment_count = max(1, min(count, len(coordinates) - 1))
        sections: list[list[list[float]]] = []
        for index in range(segment_count):
            start = round(index * (len(coordinates) - 1) / segment_count)
            end = round((index + 1) * (len(coordinates) - 1) / segment_count)
            sections.append(coordinates[start:end + 1])
        return sections

    @staticmethod
    def _roads_near_coordinates(coordinates: list[list[float]], roads: list[RoadSegment]) -> list[RoadSegment]:
        return [
            road for road in roads
            if any(
                _haversine_km(road_point, route_point) <= 12
                for road_point in road.geometry.coordinates
                for route_point in coordinates
            )
        ]

    @staticmethod
    def _incidents_near_coordinates(coordinates: list[list[float]], incidents: list[Incident]) -> list[Incident]:
        return [
            incident for incident in incidents
            if incident.verification != "REJECTED"
            and min(_haversine_km(incident.location.coordinates, point) for point in coordinates) <= 12
        ]

    @staticmethod
    def _build_intelligence_segments(
        route: OsrmRoute,
        route_index: int,
        roads: list[RoadSegment],
        incidents: list[Incident],
        weather_points: list[RouteWeatherPoint],
    ) -> list[RouteIntelligenceSegment]:
        section_count = len(weather_points) if weather_points else 8
        sections = RoutePlanningService._route_sections(route.coordinates, section_count)
        results: list[RouteIntelligenceSegment] = []
        for position, coordinates in enumerate(sections):
            distance = sum(
                _haversine_km(coordinates[index - 1], coordinates[index])
                for index in range(1, len(coordinates))
            )
            local_roads = RoutePlanningService._roads_near_coordinates(coordinates, roads)
            local_incidents = RoutePlanningService._incidents_near_coordinates(coordinates, incidents)
            weather = weather_points[min(position, len(weather_points) - 1)] if weather_points else None
            rainfall = weather.precipitation_mm_24h if weather else 0.0
            elevation = weather.elevation_m if weather else 450.0
            slope = max((road.slope_degrees for road in local_roads), default=12.0)
            condition = max(
                (road.road_condition for road in local_roads),
                key=lambda value: {"GOOD": 1, "FAIR": 2, "POOR": 3}.get(value, 2),
                default="FAIR",
            )
            advisory = model_adapter.assess_features(
                distance_km=max(distance, 0.1),
                rainfall_mm=rainfall,
                slope_deg=slope,
                elevation_m=elevation,
                incident_count=len(local_incidents),
                road_condition=condition,
            ) if weather else None
            road_risk = max((road.risk_score for road in local_roads), default=35)
            risk_score = (
                round(advisory.probability * 100 * 0.75 + road_risk * 0.25)
                if advisory and local_roads else
                round(advisory.probability * 100) if advisory else road_risk
            )
            risk_band = advisory.band if advisory else RoutingEngine._risk_band(risk_score)
            confirmed_access = [
                incident.reported_accessibility for incident in local_incidents
                if incident.verification in {"CONFIRMED", "CONTROL_CONFIRMED"}
            ]
            if RoadAccessibility.BLOCKED in confirmed_access or any(
                road.accessibility == RoadAccessibility.BLOCKED for road in local_roads
            ):
                accessibility = RoadAccessibility.BLOCKED
            elif risk_score >= 80:
                accessibility = RoadAccessibility.HIGH_RISK
            elif risk_score >= 55 or local_incidents:
                accessibility = RoadAccessibility.CAUTION
            else:
                accessibility = RoadAccessibility.OPEN
            factors: list[str] = []
            if weather:
                factors.append(f"{round(rainfall)} mm forecast rainfall/24h")
            if slope >= 18:
                factors.append(f"{round(slope)} degree terrain slope")
            if local_incidents:
                factors.append(f"{len(local_incidents)} nearby field report signal(s)")
            if local_roads:
                factors.append(f"{len(local_roads)} monitored road match(es)")
            if not factors:
                factors.append("No elevated input detected")
            confidence = min(100, 5 + (45 if weather else 0) + (30 if advisory else 0) + (20 if local_roads else 0))
            results.append(RouteIntelligenceSegment(
                id=f"OSRM-{route_index}-INT-{position + 1}",
                sequence=position + 1,
                geometry=GeoJsonLineString(coordinates=_simplify(coordinates, 220)),
                distance_km=round(distance, 1),
                accessibility=accessibility,
                risk_score=risk_score,
                risk_band=risk_band,
                ml_risk_probability=advisory.probability if advisory else None,
                predicted_delay_minutes=round(advisory.delay_minutes) if advisory else 0,
                rainfall_mm_24h=rainfall if weather else None,
                elevation_m=round(elevation) if weather else None,
                incident_count=len(local_incidents),
                incident_ids=[incident.id for incident in local_incidents],
                matched_road_ids=[road.id for road in local_roads],
                factors=factors,
                data_confidence=confidence,
            ))
        return results

    @staticmethod
    def _candidate(
        route: OsrmRoute,
        index: int,
        matched: list[RoadSegment],
        source_label: str,
        destination_label: str,
        weather_points: list[RouteWeatherPoint],
        incidents: list[Incident],
    ) -> RouteCandidate:
        distance_km = route.distance_m / 1000
        base_minutes = route.duration_seconds / 60
        heuristic_delay = sum(RoutingEngine._delay_minutes(segment) for segment in matched)
        rainfall = max((point.precipitation_mm_24h for point in weather_points), default=0)
        elevations = [point.elevation_m for point in weather_points]
        sample_coordinates = RoutePlanningService._sample_coordinates(route, len(weather_points)) if weather_points else []
        grades = [
            degrees(atan(abs(elevations[position] - elevations[position - 1]) / max(_haversine_km(sample_coordinates[position], sample_coordinates[position - 1]) * 1000, 1)))
            for position in range(1, min(len(elevations), len(sample_coordinates)))
        ]
        slope = min(45.0, max(grades, default=12.0))
        elevation = max(elevations, default=450.0)
        road_condition = max((segment.road_condition for segment in matched), key=lambda value: {"GOOD": 1, "FAIR": 2, "POOR": 3}.get(value, 2), default="FAIR")
        incident_count = RoutePlanningService._nearby_incident_count(route, incidents)
        intelligence_segments = RoutePlanningService._build_intelligence_segments(
            route, index, matched, incidents, weather_points
        )
        advisory = model_adapter.assess_features(
            distance_km=distance_km,
            rainfall_mm=rainfall,
            slope_deg=slope,
            elevation_m=elevation,
            incident_count=incident_count,
            road_condition=road_condition,
        ) if weather_points else None
        if matched:
            weighted_risk = sum(segment.risk_score * segment.distance_km for segment in matched) / max(sum(segment.distance_km for segment in matched), 1)
            risk_score = round(weighted_risk)
            highest = max(matched, key=lambda segment: segment.risk_score)
            risk_coverage = round(min(100, sum(segment.distance_km for segment in matched) / max(distance_km, 1) * 100))
        else:
            risk_score = 50
            highest = None
            risk_coverage = 0
        if advisory is not None:
            risk_score = round(advisory.probability * 100) if not matched else round(advisory.probability * 100 * 0.65 + risk_score * 0.35)
            risk_coverage = 100 if matched else 70
            delay_minutes = max(heuristic_delay, min(advisory.delay_minutes, base_minutes * 0.75))
            risk_band = advisory.band
        else:
            delay_minutes = heuristic_delay
            risk_band = RoutingEngine._risk_band(risk_score) if matched else "UNKNOWN"
        factors: list[str] = []
        if rainfall >= 45:
            factors.append(f"Heavy forecast rainfall ({round(rainfall)} mm/24h)")
        elif weather_points:
            factors.append(f"Forecast rainfall {round(rainfall)} mm/24h")
        if slope >= 18:
            factors.append(f"Steep terrain signal ({round(slope)}°)")
        if incident_count:
            factors.append(f"{incident_count} nearby incident{'s' if incident_count != 1 else ''}")
        if not factors:
            factors.append("No elevated live factor detected")
        road_names = route.road_names[:8]
        path = [source_label, *road_names, destination_label]
        return RouteCandidate(
            id=f"OSRM-{index}",
            label="External road route",
            objective="EXTERNAL",
            segment_ids=[segment.id for segment in matched],
            path=path,
            distance_km=round(distance_km, 1),
            eta_minutes=round(base_minutes + delay_minutes),
            base_travel_minutes=round(base_minutes),
            predicted_delay_minutes=round(delay_minutes),
            risk_score=risk_score,
            risk_band=risk_band,
            risk_coverage_percent=risk_coverage,
            ml_risk_probability=advisory.probability if advisory else None,
            ml_advisory_status=model_adapter.status if weather_points else "WEATHER_UNAVAILABLE",
            live_rainfall_mm_24h=rainfall if weather_points else None,
            terrain_elevation_m=round(elevation) if weather_points else None,
            risk_factors=factors,
            blocked_segments=[],
            high_risk_segments=[segment.id for segment in matched if segment.risk_score >= 55],
            highest_risk_segment_id=highest.id if highest else None,
            reason=f"ML assessed live weather, terrain and incident inputs. {factors[0]}.",
            geometry=GeoJsonLineString(coordinates=_simplify(route.coordinates)),
            intelligence_segments=intelligence_segments,
        )

    def _live_plan(self, request: RoutePlanRequest, roads: list[RoadSegment], incidents: list[Incident]) -> RoutePlanResponse:
        source = [request.source_location.longitude, request.source_location.latitude] if request.source_location else FACILITY_COORDINATES.get(request.source_facility_id)
        destination = [request.destination_location.longitude, request.destination_location.latitude] if request.destination_location else FACILITY_COORDINATES.get(request.destination_facility_id)
        source_label = request.source_location.label if request.source_location else FACILITY_LABELS.get(request.source_facility_id or "")
        destination_label = request.destination_location.label if request.destination_location else FACILITY_LABELS.get(request.destination_facility_id or "")
        if source is None or destination is None or source_label is None or destination_label is None:
            raise RuntimeError("Both origin and destination must have routable coordinates")

        external_routes = self.external.fetch_routes(source, destination)
        blocked_ids = {segment.id for segment in roads if segment.accessibility == RoadAccessibility.BLOCKED}
        confirmed_blocked_incidents = [
            incident for incident in incidents
            if incident.verification in {"CONFIRMED", "CONTROL_CONFIRMED"}
            and incident.reported_accessibility == RoadAccessibility.BLOCKED
        ]
        candidates: list[RouteCandidate] = []
        rejected: set[str] = set()
        eligible: list[tuple[int, OsrmRoute, list[RoadSegment]]] = []
        for index, external_route in enumerate(external_routes, start=1):
            matched = self._matched_segments(external_route, roads)
            route_blocked = blocked_ids.intersection(segment.id for segment in matched)
            route_incident_blocks = [
                incident.id for incident in confirmed_blocked_incidents
                if self._nearby_incident_count(external_route, [incident])
            ]
            if route_blocked or route_incident_blocks:
                rejected.update(route_blocked)
                rejected.update(route_incident_blocks)
                continue
            eligible.append((index, external_route, matched))
        if not eligible:
            raise RuntimeError("External routes intersect confirmed closures or no usable route was returned")

        route_samples = [self._sample_coordinates(route) for _, route, _ in eligible]
        flat_samples = [point for samples in route_samples for point in samples]
        weather_by_route: list[list[RouteWeatherPoint]] = [[] for _ in eligible]
        try:
            live_weather = self.weather.fetch_for_coordinates(flat_samples)
            offset = 0
            for route_index, samples in enumerate(route_samples):
                weather_by_route[route_index] = live_weather[offset:offset + len(samples)]
                offset += len(samples)
        except Exception as exc:
            logger.warning("Route weather sampling unavailable; ML route advisory degraded: %s", exc)

        incident_counts = [self._nearby_incident_count(route, incidents) for _, route, _ in eligible]
        for route_index, (index, external_route, matched) in enumerate(eligible):
            candidates.append(self._candidate(
                external_route,
                index,
                matched,
                source_label,
                destination_label,
                weather_by_route[route_index],
                incidents,
            ))

        if request.preference == RoutePreference.FASTEST_FEASIBLE:
            recommended = min(candidates, key=lambda route: route.eta_minutes)
        elif request.preference == RoutePreference.SAFETY_FIRST:
            recommended = min(candidates, key=lambda route: route.eta_minutes + route.risk_score * 5 + (100 - route.risk_coverage_percent) * 3)
        else:
            recommended = min(candidates, key=lambda route: route.eta_minutes + route.risk_score * 2 + (100 - route.risk_coverage_percent))
        recommended.label = "Recommended"
        warnings = ["External road geometry plus live route weather and ML disruption/delay inference; verified closures remain authoritative."]
        if any(route.risk_coverage_percent < 40 for route in candidates):
            warnings.append("Some route sections are outside currently monitored risk corridors; low coverage is penalized for balanced and safety-first ranking.")
        return RoutePlanResponse(
            calculated_at=datetime.now(UTC),
            data_mode=DataMode.LIVE,
            status="ROUTES_AVAILABLE",
            recommended_route_id=recommended.id,
            routes=candidates,
            warnings=warnings,
            excluded_blocked_segments=sorted(blocked_ids.union(rejected)),
            source_facility_id=request.source_facility_id,
            destination_facility_id=request.destination_facility_id,
            routing_source=self.external.provider,
            routing_status="LIVE",
            processing_steps=[
                RouteProcessingStep(key="routes", label="Alternative roads received", detail=f"{len(external_routes)} road-network options received; {len(candidates)} remained after closure checks."),
                RouteProcessingStep(key="weather", label="Live weather and terrain read", detail=f"{sum(len(points) for points in weather_by_route)} route points sampled from {self.weather.provider}.", status="COMPLETED" if any(weather_by_route) else "DEGRADED"),
                RouteProcessingStep(key="reports", label="Field reports and road updates matched", detail=f"{sum(incident_counts)} nearby non-rejected incident signals matched across the candidate routes; {len(blocked_ids)} confirmed blocked segments enforced."),
                RouteProcessingStep(key="ml", label="ML risk and delay inferred", detail=f"{model_adapter.version} assessed {sum(len(route.intelligence_segments) for route in candidates)} route sections across {len(candidates)} route options.", status="COMPLETED" if all(route.ml_risk_probability is not None for route in candidates) else "DEGRADED"),
                RouteProcessingStep(key="ranking", label="Safest feasible route ranked", detail=f"{recommended.label} selected using the {request.preference.value.replace('_', ' ').lower()} objective."),
            ],
        )

    def plan(self, request: RoutePlanRequest, roads: list[RoadSegment], incidents: list[Incident] | None = None) -> RoutePlanResponse:
        if request.routing_mode != "CURATED_ONLY":
            try:
                return self._live_plan(request, roads, incidents or [])
            except Exception as exc:
                logger.warning("Live routing unavailable; curated corridor fallback used: %s", exc)
        fallback = RoutingEngine(roads).plan(request)
        fallback.routing_status = "CURATED" if request.routing_mode == "CURATED_ONLY" else "FALLBACK"
        if request.routing_mode != "CURATED_ONLY":
            fallback.warnings.insert(0, "Live routing provider unavailable or unsafe; curated corridor fallback is in use.")
        if request.source_location is not None or request.destination_location is not None:
            fallback.warnings.append("Arbitrary NER locations require the external road-network provider; the offline graph currently covers only the pilot corridor.")
        return fallback


route_planning_service = RoutePlanningService()
