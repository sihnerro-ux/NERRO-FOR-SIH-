export type DataMode = 'LIVE' | 'SIMULATED' | 'CACHED' | 'UNAVAILABLE'
export type RoadAccessibility = 'OPEN' | 'CAUTION' | 'HIGH_RISK' | 'PARTIAL' | 'BLOCKED' | 'UNKNOWN'
export type RiskBand = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL' | 'UNKNOWN'
export type UserRole = 'CONTROL_ROOM_ADMIN' | 'FIELD_OFFICER' | 'LOGISTICS_OPERATOR' | 'DISTRICT_AUTHORITY' | 'VIEWER' | 'DRIVER'

export interface AuthUser {
  id: string
  username: string
  display_name: string
  role: UserRole
  district: string | null
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in_seconds: number
  user: AuthUser
}

export interface RoadSegment {
  id: string
  road_name: string
  from_node: string
  to_node: string
  states: string[]
  geometry: { type: 'LineString'; coordinates: number[][] }
  distance_km: number
  accessibility: RoadAccessibility
  risk_score: number
  risk_band: RiskBand
  road_condition: string
  rainfall_mm_24h: number
  slope_degrees: number
  source: string
  data_mode: DataMode
  observed_at: string
  updated_at: string
  confidence: number
  ml_risk_probability: number | null
  ml_risk_band: RiskBand | null
  ml_predicted_delay_minutes: number | null
  ml_advisory_status: 'AVAILABLE' | 'DEGRADED' | 'UNAVAILABLE'
}

export interface Vehicle {
  id: string
  registration: string
  vehicle_class: string
  status: string
  latitude: number
  longitude: number
  speed_kph: number
  gps_freshness: string
  last_position_at: string
  active_delivery_id: string | null
  data_mode: DataMode
  source: string
  position_accuracy_m: number | null
  driver_user_id: string | null
  driver_name: string | null
}

export interface VehicleTelemetry {
  vehicle_id: string
  active_delivery_id: string | null
  expected_route_id: string | null
  motion_state: 'MOVING' | 'STOPPED' | 'DELAYED' | 'STALE' | 'SIMULATED'
  gps_age_seconds: number
  stationary_minutes: number
  route_deviation_km: number | null
  on_planned_route: boolean | null
  estimated_delivery_delay_minutes: number
  position_count: number
  track: { type: 'LineString'; coordinates: number[][] }
  assessed_at: string
}

export interface VehiclePositionResponse {
  status: 'ACCEPTED'
  vehicle: Vehicle
  telemetry: VehicleTelemetry
  delivery: Delivery | null
  changed_entities: string[]
  received_at: string
}

export interface VehicleRegistrationRequest {
  registration: string
  vehicle_class: string
  latitude: number
  longitude: number
  active_delivery_id: string | null
  accuracy_m: number | null
  recorded_at: string
  source: string
}

export interface VehicleRegistrationResponse {
  status: 'REGISTERED'
  vehicle: Vehicle
  telemetry: VehicleTelemetry
  registered_at: string
}

export interface Facility {
  id: string
  name: string
  facility_type: string
  district: string
  location: { type: 'Point'; coordinates: number[] }
  source: string
  data_mode: DataMode
}

export interface Incident {
  id: string
  incident_type: string
  severity: string
  reported_accessibility: RoadAccessibility
  verification: string
  location: { type: 'Point'; coordinates: number[] }
  matched_segment_id: string | null
  description: string
  source: string
  observed_at: string
  context_snapshot: Record<string, unknown>
  photo_data_url: string | null
}

export interface Delivery {
  journey_paused: boolean
  journey_timeline: Array<{ id: string; event: string; actor: string; at: string; status: string; instruction: string }>
  id: string
  cargo_type: string
  cargo_description: string
  priority: string
  source_name: string
  destination_name: string
  vehicle_id: string
  status: string
  progress_percent: number
  planned_eta: string
  current_eta: string
  delay_minutes: number
  route_id: string
  source_facility_id?: string | null
  destination_facility_id?: string | null
  route_segment_ids: string[]
  route_geometry?: { type: 'LineString'; coordinates: number[][] } | null
  route_risk_score?: number | null
  route_risk_band?: RiskBand | null
  source_location?: { type: 'Point'; coordinates: number[] } | null
  destination_location?: { type: 'Point'; coordinates: number[] } | null
  route_distance_km?: number | null
  route_eta_minutes?: number | null
  tracking_status: 'WAITING_FOR_GPS' | 'ON_ROUTE' | 'OFF_ROUTE' | 'STOPPED' | 'AT_DESTINATION' | 'ARRIVED'
  last_tracking_update?: string | null
  instruction_status: 'NONE' | 'PENDING' | 'ACKNOWLEDGED'
  instruction_type: 'NONE' | 'INITIAL_ROUTE' | 'REROUTE' | 'HOLD'
  instruction_updated_at: string | null
  instruction_acknowledged_at: string | null
}

export interface DriverJourneyResponse {
  completed_delivery: Delivery | null
  vehicle: Vehicle | null
  delivery: Delivery | null
  telemetry: VehicleTelemetry | null
  map_snapshot: MapSnapshot
  message: string
  generated_at: string
}

export interface DeliveryImpact {
  outcome: 'REROUTED' | 'AT_RISK' | 'NO_FEASIBLE_ROUTE'
  delivery_id: string
  triggering_segment_id: string
  previous_route_id: string
  route_id?: string | null
  route_path: string[]
  route_segment_ids: string[]
  eta_minutes?: number | null
  delay_minutes: number
  message: string
}

export interface Alert {
  id: string
  severity: string
  alert_type: string
  title: string
  message: string
  related_entity_type: string
  related_entity_id: string
  acknowledged: boolean
  created_at: string
}

export interface LocalizedAlert extends Alert {
  display_title: string
  display_message: string
  language: 'en' | 'hi'
  channel: 'IN_APP_REALTIME'
}

export interface AlertFeed { language: 'en' | 'hi'; channel: string; items: LocalizedAlert[] }

export interface AdministrationSnapshot {
  generated_at: string
  users: Array<{ id: string; username: string; display_name: string; role: UserRole; district: string | null; active: boolean; created_at: string }>
  sources: Array<{ name: string; status: string; mode: string }>
  persistence: { backend: string; entity_counts: Record<string, number>; spatial: { postgis: boolean; version: string | null; geometry_storage: string } }
  ml: { status: string; detail: string; mode: string; version: string; data_mode: string; can_block_roads: boolean }
  audit_events: Array<{ id: number; event_type: string; actor: string; changed_entities: string[]; details: Record<string, unknown>; created_at: string }>
}

export interface OperationalDataImportRequest {
  filename: string
  source_name: string
  content: string
  data_mode: 'CACHED' | 'SIMULATED'
  dry_run: boolean
}

export interface OperationalDataImportResponse {
  status: 'PREVIEW_VALID' | 'APPLIED'
  filename: string
  source_name: string
  dry_run: boolean
  roads_received: number
  facilities_received: number
  roads_created: number
  roads_updated: number
  facilities_created: number
  facilities_updated: number
  changed_entities: string[]
  warnings: string[]
  processed_at: string
}

export interface Overview {
  data_mode: DataMode
  generated_at: string
  metrics: Record<string, number>
  priority_deliveries: Delivery[]
  critical_alerts: Alert[]
  connectivity: { name: string; score: number; status: string }[]
}

export interface Analytics {
  generated_at: string
  data_mode: DataMode
  summary: Record<string, number>
  state_connectivity: Array<{ state: string; monitored_segments: number; open_segments: number; caution_segments: number; high_risk_segments: number; blocked_segments: number; connectivity_score: number; incidents: number; facilities: number }>
  district_activity: Array<{ district: string; incidents: number; unverified_incidents: number; critical_incidents: number; facilities: number }>
  risk_corridors: Array<{ segment_id: string; road_name: string; corridor: string; accessibility: RoadAccessibility; operational_risk: number; ml_risk_probability: number | null; rainfall_mm_24h: number; confidence: number }>
  incident_breakdown: Record<string, number>
  event_trend: Array<{ date: string; field_reports: number; verification_actions: number; gps_updates: number; dispatches: number }>
  data_quality: Record<string, number | string>
}

export interface MapSnapshot {
  data_mode: DataMode
  generated_at: string
  road_segments: RoadSegment[]
  vehicles: Vehicle[]
  vehicle_telemetry: VehicleTelemetry[]
  facilities: Facility[]
  incidents: Incident[]
  operational_boundary: { type: 'MultiPolygon'; coordinates: number[][][][] }
}

export interface SimulationResponse {
  event: string
  message: string
  changed_entities: string[]
  overview: Overview
  map_snapshot: MapSnapshot
  disruption_summary?: {
    outcome: 'REROUTED' | 'AT_RISK' | 'NO_FEASIBLE_ROUTE'
    delivery_id: string
    blocked_segment_id: string
    route_id?: string
    route_path?: string[]
    eta_minutes?: number
    delay_minutes?: number
    message: string
  } | null
  delivery_impacts: DeliveryImpact[]
}

export interface WeatherRefreshResponse {
  status: 'LIVE' | 'CACHED'
  provider: string
  message: string
  changed_entities: string[]
  overview: Overview
  map_snapshot: MapSnapshot
  refreshed_at: string
}

export interface FieldIncidentReportRequest {
  client_report_id?: string
  incident_type: string
  severity: 'INFO' | 'WARNING' | 'CRITICAL'
  reported_accessibility: RoadAccessibility
  matched_segment_id?: string | null
  latitude?: number
  longitude?: number
  description: string
  reporter_name: string
  context_snapshot?: Record<string, unknown>
  photo_data_url?: string | null
}

export interface LocationContext {
  latitude: number
  longitude: number
  location_label: string
  state: string | null
  district: string | null
  nearest_road: { id: string; name: string; distance_km: number; accessibility: string; condition: string; data_mode: DataMode }
  nearest_facility: { id: string; name: string; type: string; distance_km: number; data_mode: DataMode }
  weather: { rainfall_mm_24h: number; precipitation_probability_max: number | null; elevation_m: number; mode: 'LIVE' | 'CACHED'; provider: string }
  predefined_context: { slope_degrees: number; road_condition: string; landslide_susceptibility: number; flood_susceptibility: number; source: string; mode: 'SIMULATED' }
  incident_context: { nearby_count: number; radius_km: number; incident_ids: string[]; mode: string }
  ml_assessment: { status: string; model_version: string; risk_probability: number | null; risk_band: string; predicted_delay_minutes: number | null; data_mode: string }
  assessed_at: string
  warnings: string[]
}

export interface IncidentVerificationRequest {
  decision: 'CONFIRM' | 'DOWNGRADE' | 'REJECT'
  reviewer_name?: string
  note?: string
}

export type RoutePreference = 'BALANCED' | 'SAFETY_FIRST' | 'FASTEST_FEASIBLE'

export interface RouteLocation {
  label: string
  latitude: number
  longitude: number
}

export interface LocationSearchResult extends RouteLocation {
  id: string
  state: string
  district: string | null
  category: string | null
  attribution: string
}

export interface RoutePlanRequest {
  source_facility_id?: string
  destination_facility_id?: string
  source_location?: RouteLocation
  destination_location?: RouteLocation
  cargo_type: string
  priority: string
  vehicle_class: string
  preference: RoutePreference
  routing_mode?: 'LIVE_WITH_FALLBACK' | 'CURATED_ONLY'
}

export interface RouteCandidate {
  id: string
  label: string
  objective: string
  segment_ids: string[]
  path: string[]
  distance_km: number
  eta_minutes: number
  base_travel_minutes: number
  predicted_delay_minutes: number
  risk_score: number
  risk_band: RiskBand
  risk_coverage_percent: number
  ml_risk_probability: number | null
  ml_advisory_status: string
  live_rainfall_mm_24h: number | null
  terrain_elevation_m: number | null
  risk_factors: string[]
  blocked_segments: string[]
  high_risk_segments: string[]
  highest_risk_segment_id: string | null
  reason: string
  geometry: { type: 'LineString'; coordinates: number[][] }
  intelligence_segments: RouteIntelligenceSegment[]
}

export interface DeliveryCreateRequest {
  cargo_type: string
  cargo_description: string
  priority: 'NORMAL' | 'HIGH' | 'CRITICAL'
  source: RouteLocation
  destination: RouteLocation
  selected_route: RouteCandidate
  vehicle_id: string | null
}

export interface DeliveryCreateResponse {
  delivery: Delivery
  changed_entities: string[]
  overview: Overview
  map_snapshot: MapSnapshot
  created_at: string
}

export interface RouteIntelligenceSegment {
  id: string
  sequence: number
  geometry: { type: 'LineString'; coordinates: number[][] }
  distance_km: number
  accessibility: RoadAccessibility
  risk_score: number
  risk_band: RiskBand
  ml_risk_probability: number | null
  predicted_delay_minutes: number
  rainfall_mm_24h: number | null
  elevation_m: number | null
  incident_count: number
  incident_ids: string[]
  matched_road_ids: string[]
  factors: string[]
  data_confidence: number
}

export interface RouteProcessingStep {
  key: string
  label: string
  detail: string
  status: 'COMPLETED' | 'DEGRADED'
}

export interface RoutePlanResponse {
  calculated_at: string
  data_mode: DataMode
  status: 'ROUTES_AVAILABLE' | 'NO_FEASIBLE_ROUTE'
  recommended_route_id: string | null
  routes: RouteCandidate[]
  warnings: string[]
  excluded_blocked_segments: string[]
  source_facility_id: string | null
  destination_facility_id: string | null
  routing_source: string
  routing_status: 'LIVE' | 'FALLBACK' | 'CURATED'
  processing_steps: RouteProcessingStep[]
}
