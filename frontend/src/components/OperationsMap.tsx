import { divIcon, latLngBounds } from 'leaflet'
import { useEffect } from 'react'
import { CircleMarker, LayerGroup, LayersControl, MapContainer, Marker, Pane, Polygon, Polyline, Popup, TileLayer, Tooltip, useMap } from 'react-leaflet'
import type { Delivery, MapSnapshot, RoadAccessibility, RouteIntelligenceSegment } from '../types/api'
import { EvidenceImage } from './EvidenceImage'

const roadColors: Record<RoadAccessibility, string> = {
  OPEN: '#22c55e', CAUTION: '#fbbf24', HIGH_RISK: '#f97316', PARTIAL: '#eab308', BLOCKED: '#ef4444', UNKNOWN: '#94a3b8',
}

function vehicleIcon(label: string) {
  return divIcon({
    className: 'vehicle-marker-shell',
    html: `<div class="vehicle-marker"><span>◆</span><b>${label}</b></div>`,
    iconSize: [82, 34],
    iconAnchor: [18, 17],
  })
}

function RouteViewport({ coordinates }: { coordinates?: number[][] }) {
  const map = useMap()
  useEffect(() => {
    if (!coordinates || coordinates.length < 2) return
    const bounds = latLngBounds(coordinates.map(([longitude, latitude]) => [latitude, longitude]))
    map.fitBounds(bounds, { padding: [45, 45], maxZoom: 11 })
  }, [coordinates, map])
  return null
}

interface Props {
  snapshot: MapSnapshot
  selectedRoadId: string | null
  onSelectRoad: (id: string) => void
  highlightedRoadIds?: string[]
  plannedRouteCoordinates?: number[][]
  plannedRouteSegments?: RouteIntelligenceSegment[]
  deliveries?: Delivery[]
}

export function OperationsMap({ snapshot, selectedRoadId, onSelectRoad, highlightedRoadIds = [], plannedRouteCoordinates, plannedRouteSegments = [], deliveries = [] }: Props) {
  const routeStart = plannedRouteCoordinates?.at(0)
  const routeEnd = plannedRouteCoordinates?.at(-1)
  const bridgeAssets = snapshot.facilities.filter((facility) => facility.facility_type === 'BRIDGE_MONITOR')
  const operationalFacilities = snapshot.facilities.filter((facility) => facility.facility_type !== 'BRIDGE_MONITOR')

  return (
    <MapContainer center={[26.2, 93.5]} zoom={6} zoomControl className="operations-map">
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <RouteViewport coordinates={plannedRouteCoordinates} />

      {plannedRouteCoordinates && plannedRouteCoordinates.length >= 2 && <Pane name="selected-route-pane" style={{ zIndex: 550 }}>
        <Polyline positions={plannedRouteCoordinates.map(([longitude, latitude]) => [latitude, longitude])} pathOptions={{ color: '#ffffff', weight: 10, opacity: 0.9 }} interactive={false} />
        {plannedRouteSegments.length === 0
          ? <Polyline positions={plannedRouteCoordinates.map(([longitude, latitude]) => [latitude, longitude])} pathOptions={{ color: '#0f766e', weight: 6, opacity: 1, dashArray: '10 7' }} />
          : plannedRouteSegments.map((segment) => (
            <Polyline key={segment.id} positions={segment.geometry.coordinates.map(([longitude, latitude]) => [latitude, longitude])} pathOptions={{ color: roadColors[segment.accessibility], weight: 7, opacity: 1 }}>
              <Tooltip sticky>Section {segment.sequence} · {segment.risk_score}% risk · {segment.accessibility.replaceAll('_', ' ')}</Tooltip>
              <Popup><strong>Route section {segment.sequence}</strong><br />{segment.distance_km} km · {segment.risk_band} risk<br />Rainfall: {segment.rainfall_mm_24h === null ? 'Unavailable' : `${Math.round(segment.rainfall_mm_24h)} mm/24h`}<br />Nearby reports: {segment.incident_count}<br />Predicted delay: {segment.predicted_delay_minutes} min<br />Confidence: {segment.data_confidence}%<br />{segment.factors.join(' · ')}</Popup>
            </Polyline>
          ))}
        {routeStart && <CircleMarker center={[routeStart[1], routeStart[0]]} radius={8} pathOptions={{ color: '#fff', fillColor: '#0891b2', fillOpacity: 1, weight: 3 }}><Tooltip permanent direction="top">Origin</Tooltip></CircleMarker>}
        {routeEnd && <CircleMarker center={[routeEnd[1], routeEnd[0]]} radius={8} pathOptions={{ color: '#fff', fillColor: '#dc2626', fillOpacity: 1, weight: 3 }}><Tooltip permanent direction="top">Destination</Tooltip></CircleMarker>}
      </Pane>}

      <LayersControl position="topright">
        <LayersControl.Overlay checked name="NER operating boundary">
          <LayerGroup>{snapshot.operational_boundary.coordinates.map((polygon, index) => (
            <Polygon key={`ner-boundary-${index}`} positions={polygon[0].map(([longitude, latitude]) => [latitude, longitude])} pathOptions={{ color: '#0f766e', weight: 2, opacity: 0.9, fillColor: '#34d399', fillOpacity: 0.035, dashArray: '8 6' }}>
              <Tooltip sticky>North Eastern Region operating boundary</Tooltip>
            </Polygon>
          ))}</LayerGroup>
        </LayersControl.Overlay>

        <LayersControl.Overlay checked name={`Active delivery routes (${deliveries.filter((item) => item.route_geometry).length})`}>
          <LayerGroup>{deliveries.filter((delivery) => delivery.route_geometry && delivery.status !== 'ARRIVED').map((delivery) => (
            <Polyline key={`delivery-route-${delivery.id}`} positions={delivery.route_geometry!.coordinates.map(([longitude, latitude]) => [latitude, longitude])} pathOptions={{ color: delivery.priority === 'CRITICAL' ? '#7c3aed' : '#0f766e', weight: 4, opacity: 0.72, dashArray: '9 7' }}>
              <Tooltip sticky>{delivery.id} · {delivery.cargo_description}</Tooltip>
              <Popup><strong>{delivery.id}</strong><br />{delivery.source_name} → {delivery.destination_name}<br />{delivery.status.replaceAll('_', ' ')} · {delivery.route_risk_score ?? 'Unknown'}% route risk<br />Vehicle: {delivery.vehicle_id}</Popup>
            </Polyline>
          ))}</LayerGroup>
        </LayersControl.Overlay>

        <LayersControl.Overlay checked name={`Vehicle trails (${snapshot.vehicle_telemetry.filter((item) => item.position_count > 1).length})`}>
          <LayerGroup>{snapshot.vehicle_telemetry.filter((item) => item.track.coordinates.length > 1).map((telemetry) => (
            <Polyline key={telemetry.vehicle_id} positions={telemetry.track.coordinates.map(([longitude, latitude]) => [latitude, longitude])} pathOptions={{ color: telemetry.on_planned_route === false ? '#dc2626' : '#0891b2', weight: 4, opacity: 0.75, dashArray: '6 6' }}>
              <Tooltip sticky>{telemetry.vehicle_id} · {telemetry.motion_state.replaceAll('_', ' ')} · {telemetry.position_count} positions</Tooltip>
            </Polyline>
          ))}</LayerGroup>
        </LayersControl.Overlay>

        <LayersControl.Overlay checked name={`Monitored roads (${snapshot.road_segments.length})`}>
          <LayerGroup>{snapshot.road_segments.map((road) => (
            <Polyline key={road.id} positions={road.geometry.coordinates.map(([longitude, latitude]) => [latitude, longitude])} pathOptions={{ color: roadColors[road.accessibility], weight: selectedRoadId === road.id || highlightedRoadIds.includes(road.id) ? 9 : 6, opacity: highlightedRoadIds.length > 0 && !highlightedRoadIds.includes(road.id) ? 0.3 : 0.88 }} eventHandlers={{ click: () => onSelectRoad(road.id) }}>
              <Tooltip sticky>{road.road_name} · {road.risk_score}% risk</Tooltip>
            </Polyline>
          ))}</LayerGroup>
        </LayersControl.Overlay>

        <LayersControl.Overlay checked name={`Hospitals and logistics sites (${operationalFacilities.length})`}>
          <LayerGroup>{operationalFacilities.map((facility) => (
            <CircleMarker key={facility.id} center={[facility.location.coordinates[1], facility.location.coordinates[0]]} radius={7} pathOptions={{ color: '#ffffff', fillColor: facility.facility_type === 'HOSPITAL' ? '#0284c7' : facility.facility_type.includes('WAREHOUSE') ? '#7c3aed' : facility.facility_type === 'RELIEF_DEPOT' ? '#ea580c' : '#059669', fillOpacity: 0.95, weight: 2 }}>
              <Popup><strong>{facility.name}</strong><br />{facility.facility_type.replace('_', ' ')} · {facility.district}</Popup>
            </CircleMarker>
          ))}</LayerGroup>
        </LayersControl.Overlay>

        <LayersControl.Overlay checked name={`Bridge and crossing monitors (${bridgeAssets.length})`}>
          <LayerGroup>{bridgeAssets.map((facility) => (
            <CircleMarker key={facility.id} center={[facility.location.coordinates[1], facility.location.coordinates[0]]} radius={8} pathOptions={{ color: '#ffffff', fillColor: '#334155', fillOpacity: 0.95, weight: 3 }}>
              <Tooltip>{facility.name}</Tooltip>
              <Popup><strong>{facility.name}</strong><br />Bridge/crossing accessibility monitor · {facility.district}<br />SIMULATED prototype asset</Popup>
            </CircleMarker>
          ))}</LayerGroup>
        </LayersControl.Overlay>

        <LayersControl.Overlay checked name={`Weather and ML risk (${snapshot.road_segments.length})`}>
          <LayerGroup>{snapshot.road_segments.map((road) => {
            const coordinate = road.geometry.coordinates[Math.floor(road.geometry.coordinates.length / 2)]
            return <CircleMarker key={`weather-${road.id}`} center={[coordinate[1], coordinate[0]]} radius={Math.max(4, Math.min(10, road.rainfall_mm_24h / 12))} pathOptions={{ color: '#ffffff', fillColor: road.data_mode === 'LIVE' ? '#0284c7' : '#64748b', fillOpacity: 0.82, weight: 2 }}>
              <Tooltip>{road.road_name} · {Math.round(road.rainfall_mm_24h)} mm/24h · {road.risk_score}% operational risk</Tooltip>
              <Popup><strong>{road.road_name} weather and risk</strong><br />Rainfall: {Math.round(road.rainfall_mm_24h)} mm/24h<br />Operational risk: {road.risk_score}% ({road.risk_band})<br />ML risk: {road.ml_risk_probability === null ? 'Unavailable' : `${Math.round(road.ml_risk_probability * 100)}%`}<br />Source: {road.source}<br />Mode: {road.data_mode}</Popup>
            </CircleMarker>
          })}</LayerGroup>
        </LayersControl.Overlay>

        <LayersControl.Overlay checked name={`Live reported incidents (${snapshot.incidents.length})`}>
          <LayerGroup>{snapshot.incidents.map((incident) => (
            <CircleMarker key={incident.id} center={[incident.location.coordinates[1], incident.location.coordinates[0]]} radius={incident.severity === 'CRITICAL' ? 11 : 9} pathOptions={{ color: incident.verification === 'UNVERIFIED' ? '#f59e0b' : '#fff7ed', fillColor: incident.severity === 'CRITICAL' ? '#dc2626' : '#f97316', fillOpacity: 0.95, weight: 3 }}>
              <Tooltip>{incident.incident_type.replaceAll('_', ' ')} · {incident.verification.replaceAll('_', ' ')}</Tooltip>
              <Popup><strong>{incident.incident_type.replaceAll('_', ' ')}</strong><br />{incident.description}<br /><b>{incident.severity}</b> · {incident.verification.replaceAll('_', ' ')}<br />Source: {incident.source}{incident.photo_data_url ? <><br /><EvidenceImage className="incident-popup-photo" source={incident.photo_data_url} /></> : null}</Popup>
            </CircleMarker>
          ))}</LayerGroup>
        </LayersControl.Overlay>

        <LayersControl.Overlay checked name={`GPS vehicles (${snapshot.vehicles.length})`}>
          <LayerGroup>{snapshot.vehicles.map((vehicle) => {
            const telemetry = snapshot.vehicle_telemetry.find((item) => item.vehicle_id === vehicle.id)
            return <Marker key={vehicle.id} position={[vehicle.latitude, vehicle.longitude]} icon={vehicleIcon(vehicle.registration)}>
              <Popup><strong>{vehicle.registration}</strong><br />{vehicle.speed_kph} km/h · {telemetry?.motion_state ?? vehicle.gps_freshness}<br />{vehicle.data_mode} · {vehicle.source}{vehicle.position_accuracy_m !== null ? <><br />Accuracy: {vehicle.position_accuracy_m} m</> : null}{telemetry?.route_deviation_km !== null && telemetry?.route_deviation_km !== undefined ? <><br />Route deviation: {telemetry.route_deviation_km} km</> : null}</Popup>
            </Marker>
          })}</LayerGroup>
        </LayersControl.Overlay>
      </LayersControl>
    </MapContainer>
  )
}
