from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class DataMode(StrEnum):
    LIVE = "LIVE"
    SIMULATED = "SIMULATED"
    CACHED = "CACHED"
    UNAVAILABLE = "UNAVAILABLE"


class RoadAccessibility(StrEnum):
    OPEN = "OPEN"
    CAUTION = "CAUTION"
    HIGH_RISK = "HIGH_RISK"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class RiskBand(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class GeoJsonLineString(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]]


class GeoJsonPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: list[float]


class RoadSegment(BaseModel):
    id: str
    road_name: str
    from_node: str
    to_node: str
    geometry: GeoJsonLineString
    distance_km: float
    accessibility: RoadAccessibility
    risk_score: int = Field(ge=0, le=100)
    risk_band: RiskBand
    road_condition: str
    rainfall_mm_24h: float
    slope_degrees: float
    source: str
    data_mode: DataMode = DataMode.SIMULATED
    observed_at: datetime
    updated_at: datetime
    confidence: int = Field(ge=0, le=100)


class Vehicle(BaseModel):
    id: str
    registration: str
    vehicle_class: str
    status: str
    latitude: float
    longitude: float
    speed_kph: float
    heading: float
    gps_freshness: str
    last_position_at: datetime
    active_delivery_id: str | None = None


class Facility(BaseModel):
    id: str
    name: str
    facility_type: str
    district: str
    location: GeoJsonPoint


class Incident(BaseModel):
    id: str
    incident_type: str
    severity: str
    reported_accessibility: RoadAccessibility
    verification: str
    location: GeoJsonPoint
    matched_segment_id: str | None
    description: str
    source: str
    data_mode: DataMode
    observed_at: datetime
    received_at: datetime


class Delivery(BaseModel):
    id: str
    cargo_type: str
    cargo_description: str
    priority: str
    source_name: str
    destination_name: str
    vehicle_id: str
    status: str
    progress_percent: int
    planned_eta: datetime
    current_eta: datetime
    delay_minutes: int
    route_id: str


class Alert(BaseModel):
    id: str
    severity: str
    alert_type: str
    title: str
    message: str
    related_entity_type: str
    related_entity_id: str
    acknowledged: bool
    created_at: datetime


class ConnectivityItem(BaseModel):
    name: str
    score: int
    status: str


class OverviewResponse(BaseModel):
    data_mode: DataMode
    generated_at: datetime
    metrics: dict[str, int]
    priority_deliveries: list[Delivery]
    critical_alerts: list[Alert]
    connectivity: list[ConnectivityItem]


class MapSnapshotResponse(BaseModel):
    data_mode: DataMode
    generated_at: datetime
    road_segments: list[RoadSegment]
    vehicles: list[Vehicle]
    facilities: list[Facility]
    incidents: list[Incident]


class SimulationResponse(BaseModel):
    event: str
    message: str
    changed_entities: list[str]
    overview: OverviewResponse
    map_snapshot: MapSnapshotResponse


class SystemStatus(BaseModel):
    status: str
    service: str
    data_mode: DataMode
    generated_at: datetime
    sources: list[dict[str, Any]]

