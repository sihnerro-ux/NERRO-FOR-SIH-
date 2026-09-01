import { divIcon } from 'leaflet'
import { CircleMarker, MapContainer, Marker, Polyline, Popup, TileLayer, Tooltip } from 'react-leaflet'
import type { MapSnapshot, RoadAccessibility } from '../types/api'

const roadColors: Record<RoadAccessibility, string> = {
  OPEN: '#22c55e',
  CAUTION: '#fbbf24',
  HIGH_RISK: '#f97316',
  PARTIAL: '#eab308',
  BLOCKED: '#ef4444',
  UNKNOWN: '#94a3b8',
}

function vehicleIcon(label: string) {
  return divIcon({
    className: 'vehicle-marker-shell',
    html: `<div class="vehicle-marker"><span>◆</span><b>${label}</b></div>`,
    iconSize: [82, 34],
    iconAnchor: [18, 17],
  })
}

interface Props {
  snapshot: MapSnapshot
  selectedRoadId: string | null
  onSelectRoad: (id: string) => void
}

export function OperationsMap({ snapshot, selectedRoadId, onSelectRoad }: Props) {
  return (
    <MapContainer center={[27.0, 92.35]} zoom={8} zoomControl={false} className="operations-map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {snapshot.road_segments.map((road) => (
        <Polyline
          key={road.id}
          positions={road.geometry.coordinates.map(([longitude, latitude]) => [latitude, longitude])}
          pathOptions={{
            color: roadColors[road.accessibility],
            weight: selectedRoadId === road.id ? 9 : 6,
            opacity: selectedRoadId === road.id ? 1 : 0.88,
          }}
          eventHandlers={{ click: () => onSelectRoad(road.id) }}
        >
          <Tooltip sticky>{road.road_name} · {road.risk_score}% risk</Tooltip>
        </Polyline>
      ))}

      {snapshot.facilities.map((facility) => (
        <CircleMarker
          key={facility.id}
          center={[facility.location.coordinates[1], facility.location.coordinates[0]]}
          radius={7}
          pathOptions={{ color: '#d9fff0', fillColor: facility.facility_type === 'HOSPITAL' ? '#38bdf8' : '#a7f3d0', fillOpacity: 1, weight: 2 }}
        >
          <Popup><strong>{facility.name}</strong><br />{facility.facility_type.replace('_', ' ')} · {facility.district}</Popup>
        </CircleMarker>
      ))}

      {snapshot.incidents.map((incident) => (
        <CircleMarker
          key={incident.id}
          center={[incident.location.coordinates[1], incident.location.coordinates[0]]}
          radius={10}
          pathOptions={{ color: '#fff7ed', fillColor: '#f97316', fillOpacity: 0.95, weight: 3 }}
        >
          <Popup><strong>{incident.incident_type.replace('_', ' ')}</strong><br />{incident.description}<br />{incident.verification.replace('_', ' ')}</Popup>
        </CircleMarker>
      ))}

      {snapshot.vehicles.map((vehicle) => (
        <Marker key={vehicle.id} position={[vehicle.latitude, vehicle.longitude]} icon={vehicleIcon(vehicle.registration)}>
          <Popup><strong>{vehicle.registration}</strong><br />{vehicle.speed_kph} km/h · {vehicle.gps_freshness}</Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}

