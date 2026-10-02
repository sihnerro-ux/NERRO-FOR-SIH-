from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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


class UserRole(StrEnum):
    CONTROL_ROOM_ADMIN = "CONTROL_ROOM_ADMIN"
    FIELD_OFFICER = "FIELD_OFFICER"
    LOGISTICS_OPERATOR = "LOGISTICS_OPERATOR"
    DISTRICT_AUTHORITY = "DISTRICT_AUTHORITY"
    VIEWER = "VIEWER"
    DRIVER = "DRIVER"


class GeoJsonLineString(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]]


class GeoJsonPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: list[float]


class GeoJsonMultiPolygon(BaseModel):
    type: Literal["MultiPolygon"] = "MultiPolygon"
    coordinates: list[list[list[list[float]]]]


class RoadSegment(BaseModel):
    id: str
    road_name: str
    from_node: str
    to_node: str
    states: list[str] = Field(default_factory=list)
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
    ml_risk_probability: float | None = Field(default=None, ge=0, le=1)
    ml_risk_band: RiskBand | None = None
    ml_predicted_delay_minutes: float | None = Field(default=None, ge=0)
    ml_advisory_status: str = "UNAVAILABLE"


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
    data_mode: DataMode = DataMode.SIMULATED
    source: str = "GPS simulator"
    position_accuracy_m: float | None = Field(default=None, ge=0)
    driver_user_id: str | None = None
    driver_name: str | None = None


class VehiclePositionRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed_kph: float = Field(default=0, ge=0, le=180)
    heading: float = Field(default=0, ge=0, lt=360)
    accuracy_m: float | None = Field(default=None, ge=0, le=5000)
    recorded_at: datetime | None = None
    source: str = Field(default="GPS_DEVICE", min_length=2, max_length=80)


class VehicleRegistrationRequest(BaseModel):
    registration: str = Field(min_length=3, max_length=40)
    vehicle_class: str = Field(min_length=3, max_length=60)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    active_delivery_id: str | None = None
    accuracy_m: float | None = Field(default=None, ge=0, le=5000)
    recorded_at: datetime | None = None
    source: str = Field(default="BROWSER_GPS", min_length=2, max_length=80)


class VehicleTelemetry(BaseModel):
    vehicle_id: str
    active_delivery_id: str | None = None
    expected_route_id: str | None = None
    motion_state: Literal["MOVING", "STOPPED", "DELAYED", "STALE", "SIMULATED"]
    gps_age_seconds: int = Field(ge=0)
    stationary_minutes: int = Field(default=0, ge=0)
    route_deviation_km: float | None = Field(default=None, ge=0)
    on_planned_route: bool | None = None
    estimated_delivery_delay_minutes: int = Field(default=0, ge=0)
    position_count: int = Field(default=0, ge=0)
    track: GeoJsonLineString
    assessed_at: datetime


class VehiclePositionResponse(BaseModel):
    status: Literal["ACCEPTED"] = "ACCEPTED"
    vehicle: Vehicle
    telemetry: VehicleTelemetry
    delivery: "Delivery | None" = None
    changed_entities: list[str] = Field(default_factory=list)
    received_at: datetime


class VehicleRegistrationResponse(BaseModel):
    status: Literal["REGISTERED"] = "REGISTERED"
    vehicle: Vehicle
    telemetry: VehicleTelemetry
    registered_at: datetime


class Facility(BaseModel):
    id: str
    name: str
    facility_type: str
    district: str
    location: GeoJsonPoint
    source: str = "NER prototype coverage dataset"
    data_mode: DataMode = DataMode.SIMULATED


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
    context_snapshot: dict[str, Any] = Field(default_factory=dict)
    photo_data_url: str | None = Field(default=None, max_length=2_500_000)


class FieldIncidentReportRequest(BaseModel):
    client_report_id: str | None = Field(default=None, min_length=8, max_length=100)
    incident_type: str = Field(min_length=3, max_length=60)
    severity: Literal["INFO", "WARNING", "CRITICAL"] = "WARNING"
    reported_accessibility: RoadAccessibility = RoadAccessibility.CAUTION
    matched_segment_id: str | None = None
    latitude: float | None = Field(default=None, ge=21, le=30.5)
    longitude: float | None = Field(default=None, ge=87.5, le=98.5)
    description: str = Field(min_length=10, max_length=600)
    reporter_name: str = Field(default="Field officer", min_length=2, max_length=80)
    context_snapshot: dict[str, Any] = Field(default_factory=dict)
    photo_data_url: str | None = Field(default=None, max_length=2_500_000)

    @model_validator(mode="after")
    def require_geotag_or_segment(self):
        has_coordinates = self.latitude is not None and self.longitude is not None
        partial_coordinates = (self.latitude is None) != (self.longitude is None)
        if partial_coordinates:
            raise ValueError("Latitude and longitude must be supplied together")
        if not has_coordinates and self.matched_segment_id is None:
            raise ValueError("A GPS/manual location or monitored road segment is required")
        return self


class LocationContextResponse(BaseModel):
    latitude: float
    longitude: float
    location_label: str
    state: str | None = None
    district: str | None = None
    nearest_road: dict[str, Any]
    nearest_facility: dict[str, Any]
    weather: dict[str, Any]
    predefined_context: dict[str, Any]
    incident_context: dict[str, Any]
    ml_assessment: dict[str, Any]
    assessed_at: datetime
    warnings: list[str] = Field(default_factory=list)


class IncidentVerificationRequest(BaseModel):
    decision: Literal["CONFIRM", "DOWNGRADE", "REJECT"]
    reviewer_name: str = Field(default="Control room officer", min_length=2, max_length=80)
    note: str = Field(default="", max_length=400)


class AlertAcknowledgementRequest(BaseModel):
    acknowledged_by: str = Field(default="Control room officer", min_length=2, max_length=80)


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthUser(BaseModel):
    id: str
    username: str
    display_name: str
    role: UserRole
    district: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in_seconds: int
    user: AuthUser


class WeatherRefreshResponse(BaseModel):
    status: Literal["LIVE", "CACHED"]
    provider: str
    message: str
    changed_entities: list[str]
    overview: "OverviewResponse"
    map_snapshot: "MapSnapshotResponse"
    refreshed_at: datetime


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
    source_facility_id: str | None = None
    destination_facility_id: str | None = None
    route_segment_ids: list[str] = Field(default_factory=list)
    route_geometry: GeoJsonLineString | None = None
    route_risk_score: int | None = Field(default=None, ge=0, le=100)
    route_risk_band: RiskBand | None = None
    source_location: GeoJsonPoint | None = None
    destination_location: GeoJsonPoint | None = None
    route_distance_km: float | None = Field(default=None, ge=0)
    route_eta_minutes: int | None = Field(default=None, ge=0)
    tracking_status: Literal["WAITING_FOR_GPS", "ON_ROUTE", "OFF_ROUTE", "STOPPED", "AT_DESTINATION", "ARRIVED"] = "WAITING_FOR_GPS"
    last_tracking_update: datetime | None = None
    instruction_status: Literal["NONE", "PENDING", "ACKNOWLEDGED"] = "NONE"
    instruction_type: Literal["NONE", "INITIAL_ROUTE", "REROUTE", "HOLD"] = "NONE"
    instruction_updated_at: datetime | None = None
    instruction_acknowledged_at: datetime | None = None
    journey_paused: bool = False
    journey_timeline: list[dict[str, Any]] = Field(default_factory=list)


class DeliveryCreateRequest(BaseModel):
    cargo_type: str = Field(min_length=2, max_length=80)
    cargo_description: str = Field(min_length=3, max_length=240)
    priority: Literal["NORMAL", "HIGH", "CRITICAL"]
    source: "RouteLocation"
    destination: "RouteLocation"
    selected_route: "RouteCandidate"
    vehicle_id: str | None = None


class DeliveryCreateResponse(BaseModel):
    delivery: Delivery
    changed_entities: list[str]
    overview: "OverviewResponse"
    map_snapshot: "MapSnapshotResponse"
    created_at: datetime


class DeliveryVehicleAssignmentRequest(BaseModel):
    vehicle_id: str = Field(min_length=3, max_length=80)


class DriverJourneyActionRequest(BaseModel):
    action: Literal["START_JOURNEY", "ACKNOWLEDGE_ROUTE", "COMPLETE_DELIVERY", "PAUSE_JOURNEY", "RESUME_JOURNEY", "REPORT_OBSTRUCTION"]
    instruction_updated_at: datetime | None = None
    description: str = Field(default="", max_length=600)


class DriverJourneyResponse(BaseModel):
    vehicle: Vehicle | None = None
    delivery: Delivery | None = None
    completed_delivery: Delivery | None = None
    telemetry: VehicleTelemetry | None = None
    map_snapshot: "MapSnapshotResponse"
    message: str
    generated_at: datetime


class DeliveryImpact(BaseModel):
    outcome: Literal["REROUTED", "AT_RISK", "NO_FEASIBLE_ROUTE"]
    delivery_id: str
    triggering_segment_id: str
    previous_route_id: str
    route_id: str | None = None
    route_path: list[str] = Field(default_factory=list)
    route_segment_ids: list[str] = Field(default_factory=list)
    eta_minutes: int | None = None
    delay_minutes: int
    message: str


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


class StateConnectivityAnalytics(BaseModel):
    state: str
    monitored_segments: int
    open_segments: int
    caution_segments: int
    high_risk_segments: int
    blocked_segments: int
    connectivity_score: int = Field(ge=0, le=100)
    incidents: int
    facilities: int


class DistrictAnalytics(BaseModel):
    district: str
    incidents: int
    unverified_incidents: int
    critical_incidents: int
    facilities: int


class RiskCorridorAnalytics(BaseModel):
    segment_id: str
    road_name: str
    corridor: str
    accessibility: RoadAccessibility
    operational_risk: int
    ml_risk_probability: float | None = None
    rainfall_mm_24h: float
    confidence: int


class AnalyticsResponse(BaseModel):
    generated_at: datetime
    data_mode: DataMode
    summary: dict[str, float | int]
    state_connectivity: list[StateConnectivityAnalytics]
    district_activity: list[DistrictAnalytics]
    risk_corridors: list[RiskCorridorAnalytics]
    incident_breakdown: dict[str, int]
    event_trend: list[dict[str, Any]]
    data_quality: dict[str, float | int | str]


class OperationalDataImportRequest(BaseModel):
    filename: str = Field(min_length=5, max_length=180)
    source_name: str = Field(min_length=3, max_length=180)
    content: str = Field(min_length=2, max_length=5_000_000)
    data_mode: Literal['CACHED', 'SIMULATED'] = 'CACHED'
    dry_run: bool = True


class OperationalDataImportResponse(BaseModel):
    status: Literal['PREVIEW_VALID', 'APPLIED']
    filename: str
    source_name: str
    dry_run: bool
    roads_received: int
    facilities_received: int
    roads_created: int
    roads_updated: int
    facilities_created: int
    facilities_updated: int
    changed_entities: list[str]
    warnings: list[str] = Field(default_factory=list)
    processed_at: datetime


class MapSnapshotResponse(BaseModel):
    data_mode: DataMode
    generated_at: datetime
    road_segments: list[RoadSegment]
    vehicles: list[Vehicle]
    vehicle_telemetry: list[VehicleTelemetry] = Field(default_factory=list)
    facilities: list[Facility]
    incidents: list[Incident]
    operational_boundary: GeoJsonMultiPolygon


class SimulationResponse(BaseModel):
    event: str
    message: str
    changed_entities: list[str]
    overview: OverviewResponse
    map_snapshot: MapSnapshotResponse
    disruption_summary: dict[str, Any] | None = None
    delivery_impacts: list[DeliveryImpact] = Field(default_factory=list)


class SystemStatus(BaseModel):
    status: str
    service: str
    data_mode: DataMode
    generated_at: datetime
    sources: list[dict[str, Any]]


class RoutePreference(StrEnum):
    BALANCED = "BALANCED"
    SAFETY_FIRST = "SAFETY_FIRST"
    FASTEST_FEASIBLE = "FASTEST_FEASIBLE"


class RouteLocation(BaseModel):
    label: str = Field(min_length=2, max_length=240)
    latitude: float = Field(ge=21, le=30.5)
    longitude: float = Field(ge=87.5, le=98.5)


class LocationSearchResult(RouteLocation):
    id: str
    state: str
    district: str | None = None
    category: str | None = None
    attribution: str = "OpenStreetMap contributors"


class RoutePlanRequest(BaseModel):
    source_facility_id: str | None = None
    destination_facility_id: str | None = None
    source_location: RouteLocation | None = None
    destination_location: RouteLocation | None = None
    cargo_type: str = "EMERGENCY_MEDICINES"
    priority: str = "CRITICAL"
    vehicle_class: str = "REFRIGERATED_TRUCK"
    preference: RoutePreference = RoutePreference.SAFETY_FIRST
    departure_at: datetime | None = None
    routing_mode: Literal["LIVE_WITH_FALLBACK", "CURATED_ONLY"] = "LIVE_WITH_FALLBACK"

    @model_validator(mode="after")
    def require_route_endpoints(self):
        if self.source_location is None and self.source_facility_id is None:
            raise ValueError("An origin facility or location is required")
        if self.destination_location is None and self.destination_facility_id is None:
            raise ValueError("A destination facility or location is required")
        return self


class RouteIntelligenceSegment(BaseModel):
    id: str
    sequence: int
    geometry: GeoJsonLineString
    distance_km: float = Field(ge=0)
    accessibility: RoadAccessibility
    risk_score: int = Field(ge=0, le=100)
    risk_band: RiskBand
    ml_risk_probability: float | None = Field(default=None, ge=0, le=1)
    predicted_delay_minutes: int = Field(default=0, ge=0)
    rainfall_mm_24h: float | None = Field(default=None, ge=0)
    elevation_m: float | None = None
    incident_count: int = Field(default=0, ge=0)
    incident_ids: list[str] = Field(default_factory=list)
    matched_road_ids: list[str] = Field(default_factory=list)
    factors: list[str] = Field(default_factory=list)
    data_confidence: int = Field(default=0, ge=0, le=100)


class RouteCandidate(BaseModel):
    id: str
    label: str
    objective: str
    segment_ids: list[str]
    path: list[str]
    distance_km: float
    eta_minutes: int
    base_travel_minutes: int
    predicted_delay_minutes: int
    risk_score: int
    risk_band: RiskBand
    risk_coverage_percent: int = Field(default=100, ge=0, le=100)
    ml_risk_probability: float | None = Field(default=None, ge=0, le=1)
    ml_advisory_status: str = "UNAVAILABLE"
    live_rainfall_mm_24h: float | None = Field(default=None, ge=0)
    terrain_elevation_m: float | None = None
    risk_factors: list[str] = Field(default_factory=list)
    blocked_segments: list[str]
    high_risk_segments: list[str]
    highest_risk_segment_id: str | None
    reason: str
    geometry: GeoJsonLineString
    intelligence_segments: list[RouteIntelligenceSegment] = Field(default_factory=list)


class RouteProcessingStep(BaseModel):
    key: str
    label: str
    detail: str
    status: Literal["COMPLETED", "DEGRADED"] = "COMPLETED"


class RoutePlanResponse(BaseModel):
    calculated_at: datetime
    data_mode: DataMode
    status: Literal["ROUTES_AVAILABLE", "NO_FEASIBLE_ROUTE"]
    recommended_route_id: str | None
    routes: list[RouteCandidate]
    warnings: list[str]
    excluded_blocked_segments: list[str]
    source_facility_id: str | None
    destination_facility_id: str | None
    routing_source: str = "CURATED_CORRIDOR_ENGINE"
    routing_status: Literal["LIVE", "FALLBACK", "CURATED"] = "CURATED"
    processing_steps: list[RouteProcessingStep] = Field(default_factory=list)
