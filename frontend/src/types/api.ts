export type DataMode = 'LIVE' | 'SIMULATED' | 'CACHED' | 'UNAVAILABLE'
export type RoadAccessibility = 'OPEN' | 'CAUTION' | 'HIGH_RISK' | 'PARTIAL' | 'BLOCKED' | 'UNKNOWN'
export type RiskBand = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL' | 'UNKNOWN'

export interface RoadSegment {
  id: string
  road_name: string
  from_node: string
  to_node: string
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
}

export interface Facility {
  id: string
  name: string
  facility_type: string
  district: string
  location: { type: 'Point'; coordinates: number[] }
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
}

export interface Delivery {
  id: string
  cargo_type: string
  cargo_description: string
  priority: string
  source_name: string
  destination_name: string
  vehicle_id: string
  status: string
  progress_percent: number
  current_eta: string
  delay_minutes: number
}

export interface Alert {
  id: string
  severity: string
  title: string
  message: string
  related_entity_id: string
  acknowledged: boolean
  created_at: string
}

export interface Overview {
  data_mode: DataMode
  generated_at: string
  metrics: Record<string, number>
  priority_deliveries: Delivery[]
  critical_alerts: Alert[]
  connectivity: { name: string; score: number; status: string }[]
}

export interface MapSnapshot {
  data_mode: DataMode
  generated_at: string
  road_segments: RoadSegment[]
  vehicles: Vehicle[]
  facilities: Facility[]
  incidents: Incident[]
}

export interface SimulationResponse {
  event: string
  message: string
  changed_entities: string[]
  overview: Overview
  map_snapshot: MapSnapshot
}

