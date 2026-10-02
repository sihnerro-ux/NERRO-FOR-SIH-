import { useEffect, useState, type FormEvent } from 'react'
import { AlertTriangle, CheckCircle2, CloudRain, Crosshair, Database, MapPin, Navigation, ShieldAlert, Sparkles } from 'lucide-react'
import { CircleMarker, LayerGroup, MapContainer, Polygon, Polyline, TileLayer, Tooltip, useMapEvents } from 'react-leaflet'
import { api } from '../services/api'
import type { FieldIncidentReportRequest, LocationContext, MapSnapshot, RoadAccessibility } from '../types/api'

const colors: Record<RoadAccessibility, string> = { OPEN: '#22c55e', CAUTION: '#fbbf24', HIGH_RISK: '#f97316', PARTIAL: '#eab308', BLOCKED: '#ef4444', UNKNOWN: '#94a3b8' }

function MapClickCapture({ onPick }: { onPick: (latitude: number, longitude: number) => void }) {
  useMapEvents({ click: (event) => onPick(event.latlng.lat, event.latlng.lng) })
  return null
}

interface Props {
  snapshot: MapSnapshot
  isOnline: boolean
  queuedCount: number
  isSubmitting: boolean
  notice: string | null
  onSubmit: (report: FieldIncidentReportRequest) => void
}

export function FieldOperationsView({ snapshot, isOnline, queuedCount, isSubmitting, notice, onSubmit }: Props) {
  const [latitude, setLatitude] = useState<number | null>(null)
  const [longitude, setLongitude] = useState<number | null>(null)
  const [context, setContext] = useState<LocationContext | null>(null)
  const [contextLoading, setContextLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [incidentType, setIncidentType] = useState('LANDSLIDE')
  const [severity, setSeverity] = useState<'INFO' | 'WARNING' | 'CRITICAL'>('WARNING')
  const [accessibility, setAccessibility] = useState<RoadAccessibility>('CAUTION')
  const [description, setDescription] = useState('')
  const [photo, setPhoto] = useState<string | null>(null)

  useEffect(() => {
    if (notice && (notice.toLowerCase().includes('submitted') || notice.toLowerCase().includes('saved'))) {
      setDescription('')
      setPhoto(null)
    }
  }, [notice])

  const assessPoint = async (nextLatitude: number, nextLongitude: number) => {
    if (nextLatitude < 21 || nextLatitude > 30.5 || nextLongitude < 87.5 || nextLongitude > 98.5) {
      setError('Select a point inside the NER operating boundary.')
      return
    }
    setLatitude(nextLatitude)
    setLongitude(nextLongitude)
    setContext(null)
    setError(null)
    if (!isOnline) {
      setError('Offline: the geotag is saved, but live enrichment will run when the report synchronizes.')
      return
    }
    setContextLoading(true)
    try {
      setContext(await api.locationContext(nextLatitude, nextLongitude))
    } catch {
      setError('This point could not be verified as an NER location, or live context services are unavailable.')
    } finally {
      setContextLoading(false)
    }
  }

  const useGps = () => {
    if (!navigator.geolocation) { setError('GPS is not available in this browser.'); return }
    setContextLoading(true)
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => void assessPoint(coords.latitude, coords.longitude),
      () => { setContextLoading(false); setError('GPS permission was denied or the current position is unavailable.') },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 },
    )
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (latitude === null || longitude === null || description.trim().length < 10) return
    onSubmit({
      incident_type: incidentType, severity, reported_accessibility: accessibility,
      matched_segment_id: context && context.nearest_road.distance_km <= 15 ? context.nearest_road.id : null,
      latitude, longitude, description: description.trim(), reporter_name: 'Field officer',
      context_snapshot: context ? context as unknown as Record<string, unknown> : {},
      photo_data_url: photo,
    })
  }

  const choosePhoto = (file?: File) => {
    if (!file) return
    if (!file.type.startsWith('image/')) { setError('Choose an image file for field evidence.'); return }
    if (file.size > 1_500_000) { setError('Photo must be smaller than 1.5 MB for reliable low-network synchronization.'); return }
    const reader = new FileReader()
    reader.onload = () => { setPhoto(String(reader.result)); setError(null) }
    reader.onerror = () => setError('The photograph could not be read.')
    reader.readAsDataURL(file)
  }

  return <section className="field-operations">
    <div className="field-flow-strip"><span className={latitude !== null ? 'done' : ''}><CheckCircle2 size={15} />1. Select location</span><i /><span className={context ? 'done' : ''}><Database size={15} />2. Read context</span><i /><span className={description.trim().length >= 10 ? 'done' : ''}><ShieldAlert size={15} />3. Describe incident</span><i /><span className={notice ? 'done' : ''}><Navigation size={15} />4. Submit for verification</span></div>
    <div className="field-workspace">
      <article className="field-map-card">
        <div className="module-card-head"><div><p className="eyebrow">GEOTAGGED REPORTING</p><h2>Click the incident location</h2><p>Choose any point inside the NER boundary. Existing roads, facilities and reports remain visible for reference.</p></div><button className="secondary" onClick={useGps} disabled={contextLoading}><Crosshair size={15} /> Use current GPS</button></div>
        <div className="field-map">
          <MapContainer center={[26.15, 93.2]} zoom={6} className="operations-map">
            <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <MapClickCapture onPick={(lat, lon) => void assessPoint(lat, lon)} />
            {snapshot.operational_boundary.coordinates.map((polygon, index) => <Polygon key={index} positions={polygon[0].map(([lon, lat]) => [lat, lon])} pathOptions={{ color: '#0f766e', weight: 2, fillColor: '#34d399', fillOpacity: .04, dashArray: '8 6' }} />)}
            <LayerGroup>{snapshot.road_segments.map((road) => <Polyline key={road.id} positions={road.geometry.coordinates.map(([lon, lat]) => [lat, lon])} pathOptions={{ color: colors[road.accessibility], weight: 4, opacity: .72 }}><Tooltip>{road.road_name} · {road.risk_score}% risk</Tooltip></Polyline>)}</LayerGroup>
            <LayerGroup>{snapshot.facilities.map((facility) => <CircleMarker key={facility.id} center={[facility.location.coordinates[1], facility.location.coordinates[0]]} radius={5} pathOptions={{ color: '#fff', fillColor: facility.facility_type === 'HOSPITAL' ? '#0284c7' : '#7c3aed', fillOpacity: .9 }}><Tooltip>{facility.name}</Tooltip></CircleMarker>)}</LayerGroup>
            <LayerGroup>{snapshot.incidents.filter((incident) => incident.verification !== 'REJECTED').map((incident) => <CircleMarker key={incident.id} center={[incident.location.coordinates[1], incident.location.coordinates[0]]} radius={7} pathOptions={{ color: '#fff', fillColor: '#ef4444', fillOpacity: .9 }}><Tooltip>{incident.incident_type.replaceAll('_', ' ')}</Tooltip></CircleMarker>)}</LayerGroup>
            {latitude !== null && longitude !== null && <CircleMarker center={[latitude, longitude]} radius={11} pathOptions={{ color: '#fff', fillColor: '#dc2626', fillOpacity: 1, weight: 4 }}><Tooltip permanent direction="top">New report</Tooltip></CircleMarker>}
          </MapContainer>
        </div>
      </article>

      <aside className="field-report-sidebar">
        <article className="context-card">
          <div className="context-head"><div><p className="eyebrow">LOCATION INTELLIGENCE</p><h2>{contextLoading ? 'Reading live inputs…' : context ? context.location_label.split(',').slice(0, 2).join(',') : 'Select a map point'}</h2></div><MapPin size={19} /></div>
          {contextLoading && <div className="context-loading"><span /><p>Reverse geocoding, weather, terrain, reports and ML assessment are running.</p></div>}
          {!contextLoading && context && <div className="context-grid">
            <div><span>District / State</span><strong>{context.district ?? 'Unknown'} · {context.state ?? 'Unknown'}</strong></div>
            <div><span>Nearest monitored road</span><strong>{context.nearest_road.name} · {context.nearest_road.distance_km} km</strong><small>{context.nearest_road.accessibility} · {context.nearest_road.data_mode}</small></div>
            <div><span>Nearest facility</span><strong>{context.nearest_facility.name}</strong><small>{context.nearest_facility.distance_km} km · {context.nearest_facility.data_mode}</small></div>
            <div><span>Live weather</span><strong>{context.weather.rainfall_mm_24h} mm rainfall</strong><small>{context.weather.elevation_m} m elevation · {context.weather.mode}</small></div>
            <div><span>Prototype terrain risk</span><strong>Landslide {context.predefined_context.landslide_susceptibility}% · Flood {context.predefined_context.flood_susceptibility}%</strong><small>{context.predefined_context.slope_degrees}° slope · SIMULATED</small></div>
            <div className="ml-context"><span><Sparkles size={12} /> ML assessment</span><strong>{context.ml_assessment.risk_probability === null ? 'Unavailable' : `${Math.round(context.ml_assessment.risk_probability * 100)}% · ${context.ml_assessment.risk_band}`}</strong><small>Predicted delay {context.ml_assessment.predicted_delay_minutes ?? '—'} min · {context.ml_assessment.model_version}</small></div>
            <div><span>Nearby operational reports</span><strong>{context.incident_context.nearby_count} within {context.incident_context.radius_km} km</strong><small>Live operational state</small></div>
          </div>}
          {error && <div className="context-error"><AlertTriangle size={14} />{error}</div>}
        </article>

        <form className="field-incident-form" onSubmit={submit}>
          <div><p className="eyebrow">INCIDENT DETAILS</p><h2>Complete field report</h2></div>
          <div className="field-form-row"><label>Incident type<select value={incidentType} onChange={(event) => setIncidentType(event.target.value)}><option>LANDSLIDE</option><option>FLOODING</option><option>ROAD_DAMAGE</option><option>BRIDGE_DAMAGE</option><option>TRAFFIC_CONGESTION</option><option>OTHER</option></select></label><label>Severity<select value={severity} onChange={(event) => setSeverity(event.target.value as typeof severity)}><option>INFO</option><option>WARNING</option><option>CRITICAL</option></select></label></div>
          <label>Observed accessibility<select value={accessibility} onChange={(event) => setAccessibility(event.target.value as RoadAccessibility)}><option value="OPEN">Open</option><option value="CAUTION">Caution</option><option value="HIGH_RISK">High risk</option><option value="PARTIAL">Partial access</option><option value="BLOCKED">Blocked</option><option value="UNKNOWN">Unknown</option></select></label>
          <label>On-ground description<textarea required minLength={10} maxLength={600} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Describe road condition, obstruction, affected lane, nearby landmark and immediate safety concern." /></label>
          <label className="photo-capture">Field photograph (optional)<input type="file" accept="image/*" capture="environment" onChange={(event) => choosePhoto(event.target.files?.[0])} />{photo && <span><img src={photo} alt="Selected field evidence" /><button type="button" onClick={() => setPhoto(null)}>Remove photograph</button></span>}</label>
          <div className="report-provenance"><span><MapPin size={13} />{latitude === null ? 'No location selected' : `${latitude.toFixed(5)}, ${longitude?.toFixed(5)}`}</span><span className={isOnline ? 'online' : 'offline'}>{isOnline ? 'ONLINE · LIVE ENRICHMENT' : `OFFLINE · ${queuedCount} QUEUED`}</span></div>
          {notice && <div className="field-submit-notice">{notice}</div>}
          <button className="primary" disabled={isSubmitting || latitude === null || description.trim().length < 10}>{isSubmitting ? 'Submitting report…' : isOnline ? 'Submit for verification' : 'Save report offline'}</button>
        </form>
      </aside>
    </div>
  </section>
}
