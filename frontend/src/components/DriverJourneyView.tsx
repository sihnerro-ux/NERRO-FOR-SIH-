import { useState, type FormEvent } from 'react'
import { AlertTriangle, CheckCircle2, Clock3, MapPin, Navigation, PackageCheck, Radio, Satellite, ShieldAlert, Truck } from 'lucide-react'
import type { DriverJourneyResponse, VehicleRegistrationRequest } from '../types/api'
import { OperationsMap } from './OperationsMap'
import { JourneyTimeline } from './JourneyTimeline'
import { DriverLocationSharing } from './DriverLocationSharing'

type RegistrationDraft = Pick<VehicleRegistrationRequest, 'registration' | 'vehicle_class'>
type JourneyAction = 'START_JOURNEY' | 'ACKNOWLEDGE_ROUTE' | 'COMPLETE_DELIVERY' | 'PAUSE_JOURNEY' | 'RESUME_JOURNEY' | 'REPORT_OBSTRUCTION'

interface Props {
  journey: DriverJourneyResponse
  busy: boolean
  notice: string | null
  onRegister: (draft: RegistrationDraft) => void
  onRegisterDemo: (draft: RegistrationDraft, location: DemoLocation) => void
  onShareGps: (vehicleId: string) => void
  onAdvanceDemoGps: (vehicleId: string) => void
  onAction: (action: JourneyAction, description?: string) => void
}

export interface DemoLocation { label: string; latitude: number; longitude: number }
const DEMO_LOCATIONS: DemoLocation[] = [
  { label: 'Guwahati, Assam', latitude: 26.1445, longitude: 91.7362 },
  { label: 'Shillong, Meghalaya', latitude: 25.5788, longitude: 91.8933 },
  { label: 'Imphal, Manipur', latitude: 24.817, longitude: 93.9368 },
  { label: 'Agartala, Tripura', latitude: 23.8315, longitude: 91.2868 },
  { label: 'Itanagar, Arunachal Pradesh', latitude: 27.0844, longitude: 93.6053 },
]

function timeLabel(value: string) {
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

export function DriverJourneyView({ journey, busy, notice, onRegister, onRegisterDemo, onShareGps, onAdvanceDemoGps, onAction }: Props) {
  const [registration, setRegistration] = useState('')
  const [vehicleClass, setVehicleClass] = useState('GENERAL_TRUCK')
  const [obstruction, setObstruction] = useState('')
  const [demoLocationIndex, setDemoLocationIndex] = useState(0)
  const { vehicle, delivery, telemetry } = journey

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (registration.trim()) onRegister({ registration: registration.trim(), vehicle_class: vehicleClass })
  }

  if (!vehicle) return <section className="driver-workspace">
    <article className="driver-onboarding">
      <div className="driver-onboarding-copy"><Satellite size={29} /><p className="eyebrow">REAL GPS ONBOARDING</p><h2>Connect this vehicle</h2><p>No vehicle is fabricated for this account. Register the vehicle using this phone's live location; it will then appear in the logistics dispatch pool.</p></div>
      <form onSubmit={submit}>
        <label>Registration number<input required minLength={3} value={registration} onChange={(event) => setRegistration(event.target.value)} placeholder="AS-01-AB-1234" /></label>
        <label>Vehicle type<select value={vehicleClass} onChange={(event) => setVehicleClass(event.target.value)}><option value="GENERAL_TRUCK">General truck</option><option value="REFRIGERATED_TRUCK">Refrigerated truck</option><option value="RELIEF_TRUCK">Relief truck</option><option value="AMBULANCE">Ambulance</option></select></label>
        <button className="primary" disabled={busy}><Satellite size={16} />{busy ? 'Reading live GPS…' : 'Register with phone GPS'}</button>
        <div className="demo-gps-panel"><div><strong>Testing outside North East India?</strong><span>Use an explicitly simulated NER position. It stays labelled DEMO and never appears as live GPS.</span></div><select aria-label="NER demo location" value={demoLocationIndex} onChange={(event) => setDemoLocationIndex(Number(event.target.value))}>{DEMO_LOCATIONS.map((location, index) => <option value={index} key={location.label}>{location.label}</option>)}</select><button type="button" disabled={busy || !registration.trim()} onClick={() => onRegisterDemo({ registration: registration.trim(), vehicle_class: vehicleClass }, DEMO_LOCATIONS[demoLocationIndex])}>Use demo GPS</button></div>
      </form>
      {notice && <div className="driver-notice"><Radio size={15} />{notice}</div>}
    </article>
  </section>

  return <section className="driver-workspace">
    {vehicle.data_mode === 'LIVE' && <DriverLocationSharing key={`${vehicle.id}:${delivery?.id ?? 'idle'}`} vehicleId={vehicle.id} deliveryId={delivery?.id ?? null} />}
    {journey.completed_delivery && !delivery && <article className="driver-route-card"><h2>Last delivery completed</h2><JourneyTimeline delivery={journey.completed_delivery} /></article>}
    <div className="driver-status-strip"><Radio size={17} /><span><strong>{vehicle.registration} connected</strong>{vehicle.data_mode === 'SIMULATED' ? `Demo GPS · ${journey.message}` : journey.message}</span><b className={`gps-state ${(telemetry?.motion_state ?? vehicle.gps_freshness).toLowerCase()}`}>{vehicle.data_mode === 'SIMULATED' ? 'DEMO GPS' : telemetry?.motion_state ?? vehicle.gps_freshness}</b></div>
    {notice && <div className="driver-notice"><Radio size={15} />{notice}</div>}

    {!delivery ? <article className="driver-waiting"><Truck size={34} /><h2>Waiting for a delivery assignment</h2><p>Your {vehicle.data_mode === 'SIMULATED' ? 'demo vehicle' : 'real vehicle and latest GPS position'} is visible to the logistics control room. Dispatch can now assign a delivery.</p>{vehicle.data_mode === 'LIVE' && <button className="primary" disabled={busy} onClick={() => onShareGps(vehicle.id)}><Satellite size={16} />Share current GPS</button>}</article> : <>
      {delivery.instruction_status === 'PENDING' && <article className={`driver-instruction ${delivery.instruction_type === 'REROUTE' ? 'reroute' : ''}`}><ShieldAlert size={22} /><div><p>{delivery.instruction_type === 'HOLD' ? 'SAFETY HOLD' : delivery.instruction_type === 'REROUTE' ? 'NEW REROUTE INSTRUCTION' : 'ROUTE ASSIGNMENT'}</p><strong>{delivery.instruction_type === 'HOLD' ? 'Do not depart. Dispatch has not found a feasible route.' : delivery.instruction_type === 'REROUTE' ? 'The control tower changed your route after live risk reassessment.' : 'Review the assigned route before departure.'}</strong><span>Updated {delivery.instruction_updated_at ? timeLabel(delivery.instruction_updated_at) : 'just now'}</span></div><button disabled={busy} onClick={() => onAction('ACKNOWLEDGE_ROUTE')}><CheckCircle2 size={16} />{delivery.instruction_type === 'HOLD' ? 'Acknowledge hold' : 'Acknowledge route'}</button></article>}
      {delivery.tracking_status === 'AT_DESTINATION' && <div className="driver-notice" role="status">You are near the destination. Confirm the shipment handover with Mark delivered; GPS alone does not complete this delivery.</div>}

      <div className="driver-summary-grid">
        {delivery.instruction_type === 'HOLD' && <div role="alert">Journey held: no feasible route is available. Wait for a new route from dispatch. Acknowledging this notice does not authorize departure.</div>}
        <article><PackageCheck size={18} /><span>Delivery</span><strong>{delivery.id}</strong><small>{delivery.cargo_description}</small></article>
        <article><Navigation size={18} /><span>Progress</span><strong>{delivery.progress_percent}%</strong><small>{delivery.tracking_status.replaceAll('_', ' ')}</small></article>
        <article><Clock3 size={18} /><span>Current ETA</span><strong>{timeLabel(delivery.current_eta)}</strong><small>{delivery.delay_minutes > 0 ? `+${delivery.delay_minutes} min predicted delay` : 'On schedule'}</small></article>
        <article><AlertTriangle size={18} /><span>Route risk</span><strong>{delivery.route_risk_score ?? 0}%</strong><small>{delivery.route_risk_band ?? 'UNKNOWN'} · live reassessment</small></article>
      </div>

      <article className="driver-route-card">
        <div className="driver-route-head">
          <strong>{delivery.journey_paused ? 'Journey paused' : delivery.status.replaceAll('_', ' ')}</strong>
          {delivery.journey_paused ? <button className="secondary" disabled={busy || delivery.instruction_type === 'HOLD' || delivery.instruction_status === 'PENDING'} onClick={() => onAction('RESUME_JOURNEY')}>Resume journey</button> : <button className="secondary" disabled={busy || !['IN_TRANSIT', 'DELAYED', 'AT_RISK', 'REROUTING'].includes(delivery.status)} onClick={() => onAction('PAUSE_JOURNEY')}>Pause journey</button>}
        </div>
        <form className="driver-route-head" onSubmit={event => { event.preventDefault(); onAction('REPORT_OBSTRUCTION', obstruction) }}>
          <label>Report road blocked at last recorded vehicle position (requires verification)<textarea required minLength={10} maxLength={600} value={obstruction} onChange={event => setObstruction(event.target.value)} placeholder="Describe the obstruction blocking the road" /></label>
          <button className="secondary" disabled={busy || obstruction.trim().length < 10}>Submit for verification</button>
        </form>
        <JourneyTimeline delivery={delivery} />
        <div className="driver-route-head"><div><p className="eyebrow">ASSIGNED JOURNEY</p><h2>{delivery.source_name} → {delivery.destination_name}</h2><span>Weather, verified incidents, monitored roads and ML advisory are included in this route.</span></div><button className="secondary" disabled={busy} onClick={() => vehicle.data_mode === 'SIMULATED' ? onAdvanceDemoGps(vehicle.id) : onShareGps(vehicle.id)}><Satellite size={16} />{vehicle.data_mode === 'SIMULATED' ? 'Advance demo GPS' : 'Update live GPS'}</button></div>
        <div className="driver-map"><OperationsMap snapshot={journey.map_snapshot} selectedRoadId={null} onSelectRoad={() => undefined} highlightedRoadIds={delivery.instruction_type === 'HOLD' ? [] : delivery.route_segment_ids} plannedRouteCoordinates={delivery.instruction_type === 'HOLD' ? undefined : delivery.route_geometry?.coordinates} deliveries={delivery.instruction_type === 'HOLD' ? [] : [delivery]} /></div>
        <div className="driver-route-footer"><span><MapPin size={14} />{vehicle.data_mode === 'SIMULATED' ? 'Demo' : 'Live'} GPS: {vehicle.latitude.toFixed(5)}, {vehicle.longitude.toFixed(5)} · {telemetry?.gps_age_seconds ?? 0}s old</span><div>{delivery.status === 'DISPATCHED' && <button className="primary" disabled={busy || delivery.instruction_status === 'PENDING'} onClick={() => onAction('START_JOURNEY')}><Navigation size={16} />Start journey</button>}<button className="secondary" disabled={busy || delivery.status === 'ARRIVED'} onClick={() => { if (window.confirm('Confirm that the shipment has reached its destination?')) onAction('COMPLETE_DELIVERY') }}><CheckCircle2 size={16} />Mark delivered</button></div></div>
      </article>
    </>}
  </section>
}
