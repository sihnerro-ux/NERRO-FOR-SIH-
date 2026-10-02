from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable

import networkx as nx

from app.domain.models import (
    DataMode,
    GeoJsonLineString,
    RiskBand,
    RoadAccessibility,
    RoadSegment,
    RouteCandidate,
    RoutePlanRequest,
    RoutePlanResponse,
    RoutePreference,
)


FACILITY_NODES = {
    "FAC-GHY-MED": "GUWAHATI",
    "FAC-TEZ-HUB": "TEZPUR",
    "FAC-BOM-RELIEF": "BOMDILA",
    "FAC-TAW-HOSP": "TAWANG",
}

ROAD_SPEED_KPH = {
    "GOOD": 48.0,
    "FAIR": 34.0,
    "POOR": 24.0,
}


class RoutingEngine:
    """Builds a directed graph and returns defensible route alternatives."""

    def __init__(self, road_segments: list[RoadSegment]):
        self.road_segments = road_segments
        self.graph = self._build_graph(road_segments)

    @staticmethod
    def _build_graph(road_segments: list[RoadSegment]) -> nx.DiGraph:
        graph = nx.DiGraph()
        for segment in road_segments:
            if segment.accessibility == RoadAccessibility.BLOCKED:
                continue
            attrs = {"segment": segment}
            graph.add_edge(segment.from_node, segment.to_node, **attrs)
            graph.add_edge(segment.to_node, segment.from_node, **attrs)
        return graph

    @staticmethod
    def _base_minutes(segment: RoadSegment) -> float:
        speed = ROAD_SPEED_KPH.get(segment.road_condition, 30.0)
        if segment.accessibility in {RoadAccessibility.CAUTION, RoadAccessibility.PARTIAL}:
            speed *= 0.75
        if segment.accessibility == RoadAccessibility.HIGH_RISK:
            speed *= 0.62
        return segment.distance_km / max(speed, 8.0) * 60

    @staticmethod
    def _delay_minutes(segment: RoadSegment) -> float:
        weather_delay = max(0.0, segment.rainfall_mm_24h - 20.0) * 0.32
        condition_delay = {"GOOD": 0.0, "FAIR": 7.0, "POOR": 18.0}.get(segment.road_condition, 8.0)
        accessibility_delay = {
            RoadAccessibility.OPEN: 0.0,
            RoadAccessibility.CAUTION: 12.0,
            RoadAccessibility.PARTIAL: 28.0,
            RoadAccessibility.HIGH_RISK: 42.0,
            RoadAccessibility.UNKNOWN: 35.0,
        }.get(segment.accessibility, 0.0)
        rules_delay = weather_delay + condition_delay + accessibility_delay
        ml_delay = float(segment.ml_predicted_delay_minutes or 0.0) if segment.ml_advisory_status == "AVAILABLE" else 0.0
        return max(rules_delay, ml_delay)

    @staticmethod
    def _effective_risk(segment: RoadSegment) -> float:
        ml_risk = float(segment.ml_risk_probability or 0.0) * 100 if segment.ml_advisory_status == "AVAILABLE" else 0.0
        return max(float(segment.risk_score), ml_risk)

    @classmethod
    def _weight(cls, objective: str) -> Callable[[str, str, dict], float]:
        def weight(_u: str, _v: str, edge: dict) -> float:
            segment: RoadSegment = edge["segment"]
            travel = cls._base_minutes(segment) + cls._delay_minutes(segment)
            risk_exposure = cls._effective_risk(segment) * segment.distance_km / 100.0
            unknown_penalty = 160.0 if segment.accessibility == RoadAccessibility.UNKNOWN else 0.0
            if objective == "FASTEST":
                return travel + risk_exposure * 0.25 + unknown_penalty
            if objective == "SAFEST":
                return travel + risk_exposure * 7.0 + unknown_penalty
            return travel + risk_exposure * 2.0 + unknown_penalty

        return weight

    def _path_for(self, source: str, destination: str, objective: str) -> list[str] | None:
        try:
            return nx.dijkstra_path(self.graph, source, destination, weight=self._weight(objective))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def _segments_for_path(self, path: list[str]) -> list[RoadSegment]:
        return [self.graph[path[index]][path[index + 1]]["segment"] for index in range(len(path) - 1)]

    @staticmethod
    def _geometry(path: list[str], segments: list[RoadSegment]) -> GeoJsonLineString:
        coordinates: list[list[float]] = []
        for index, segment in enumerate(segments):
            segment_coordinates = segment.geometry.coordinates
            if segment.from_node != path[index]:
                segment_coordinates = list(reversed(segment_coordinates))
            if coordinates and coordinates[-1] == segment_coordinates[0]:
                coordinates.extend(segment_coordinates[1:])
            else:
                coordinates.extend(segment_coordinates)
        return GeoJsonLineString(coordinates=coordinates)

    @staticmethod
    def _risk_band(score: int) -> RiskBand:
        if score < 25:
            return RiskBand.LOW
        if score < 55:
            return RiskBand.MODERATE
        if score < 80:
            return RiskBand.HIGH
        return RiskBand.CRITICAL

    def _candidate(self, path: list[str], objective: str, sequence: int) -> RouteCandidate:
        segments = self._segments_for_path(path)
        distance = sum(segment.distance_km for segment in segments)
        base_minutes = sum(self._base_minutes(segment) for segment in segments)
        delay_minutes = sum(self._delay_minutes(segment) for segment in segments)
        distance_weighted_risk = sum(self._effective_risk(segment) * segment.distance_km for segment in segments) / max(distance, 1)
        risk_score = round(distance_weighted_risk)
        highest = max(segments, key=self._effective_risk)
        high_risk = [segment.id for segment in segments if self._effective_risk(segment) >= 55]

        if objective == "FASTEST":
            reason = "Lowest estimated journey time across currently accessible segments."
            label = "Fastest feasible"
        elif objective == "SAFEST":
            reason = "Lowest cumulative disruption exposure, with additional weight on risky and uncertain segments."
            label = "Lowest risk"
        else:
            reason = "Balances travel time with weather, road condition and disruption exposure."
            label = "Balanced"

        return RouteCandidate(
            id=f"CANDIDATE-{objective}-{sequence}",
            label=label,
            objective=objective,
            segment_ids=[segment.id for segment in segments],
            path=path,
            distance_km=round(distance, 1),
            eta_minutes=round(base_minutes + delay_minutes),
            base_travel_minutes=round(base_minutes),
            predicted_delay_minutes=round(delay_minutes),
            risk_score=risk_score,
            risk_band=self._risk_band(risk_score),
            blocked_segments=[],
            high_risk_segments=high_risk,
            highest_risk_segment_id=highest.id,
            reason=reason,
            geometry=self._geometry(path, segments),
        )

    def plan(self, request: RoutePlanRequest) -> RoutePlanResponse:
        source = FACILITY_NODES.get(request.source_facility_id)
        destination = FACILITY_NODES.get(request.destination_facility_id)
        blocked = [segment.id for segment in self.road_segments if segment.accessibility == RoadAccessibility.BLOCKED]
        warnings = ["Route risk and delay values use curated simulated data for the pilot corridor."]

        if source is None or destination is None:
            return RoutePlanResponse(
                calculated_at=datetime.now(UTC),
                data_mode=DataMode.SIMULATED,
                status="NO_FEASIBLE_ROUTE",
                recommended_route_id=None,
                routes=[],
                warnings=warnings + ["The selected facility is not connected to the pilot road graph."],
                excluded_blocked_segments=blocked,
                source_facility_id=request.source_facility_id,
                destination_facility_id=request.destination_facility_id,
            )

        candidates: list[RouteCandidate] = []
        seen_paths: set[tuple[str, ...]] = set()
        for index, objective in enumerate(("BALANCED", "FASTEST", "SAFEST"), start=1):
            path = self._path_for(source, destination, objective)
            if path and tuple(path) not in seen_paths:
                candidates.append(self._candidate(path, objective, index))
                seen_paths.add(tuple(path))

        if not candidates:
            return RoutePlanResponse(
                calculated_at=datetime.now(UTC),
                data_mode=DataMode.SIMULATED,
                status="NO_FEASIBLE_ROUTE",
                recommended_route_id=None,
                routes=[],
                warnings=warnings + ["No accessible path connects the selected facilities."],
                excluded_blocked_segments=blocked,
                source_facility_id=request.source_facility_id,
                destination_facility_id=request.destination_facility_id,
            )

        preferred_objective = {
            RoutePreference.SAFETY_FIRST: "SAFEST",
            RoutePreference.FASTEST_FEASIBLE: "FASTEST",
            RoutePreference.BALANCED: "BALANCED",
        }[request.preference]
        recommended = next((route for route in candidates if route.objective == preferred_objective), candidates[0])
        recommended.label = "Recommended"
        return RoutePlanResponse(
            calculated_at=datetime.now(UTC),
            data_mode=DataMode.SIMULATED,
            status="ROUTES_AVAILABLE",
            recommended_route_id=recommended.id,
            routes=candidates,
            warnings=warnings,
            excluded_blocked_segments=blocked,
            source_facility_id=request.source_facility_id,
            destination_facility_id=request.destination_facility_id,
        )
