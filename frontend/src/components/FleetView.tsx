import { useState, type FormEvent } from 'react'
import { AlertTriangle, Clock3, Gauge, MapPinned, Radio, Route, Satellite, Truck } from 'lucide-react'
import type { Delivery, Vehicle, VehicleRegistrationRequest, VehicleTelemetry } from '../types/api'

function timeLabel(value: string) {
  return new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value))
}

type RegistrationDraft = Pick<VehicleRegistrationRequest, 'registration' | 'vehicle_class' | 'active_delivery_id'>

interface Props {
  vehicles: Vehicle[]
  deliveries: Delivery[]
  telemetry: VehicleTelemetry[]
  canManageGps: boolean
  busy: boolean
  updatingVehicleId: string | null
  notice: string | null
  onRegister: (draft: RegistrationDraft) => void
  onShareGps: (vehicleId: string) => void
  onViewMap: () => void
}

export function FleetView({ vehicles, deliveries, telemetry, canManageGps, busy, updatingVehicleId, notice, onRegister, onShareGps, onViewMap }: Props) {
  const [registration, setRegistration] = useState('')
  const [vehicleClass, setVehicleClass] = useState('GENERAL_TRUCK')
  const [deliveryId, setDeliveryId] = useState('')

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!registration.trim()) return
    onRegister({ registration: registration.trim(), vehicle_class: vehicleClass, active_delivery_id: deliveryId || null })
  }

  return (
    <section className="module-view" aria-label="Fleet module">
      <div className="fleet-status-strip"><Radio size={17} /><div><strong>Real telemetry monitor</strong><span>No vehicle is created until a browser or registered GPS device supplies its position. The map refreshes every 10 seconds.</span></div><b>{vehicles.length} registered · {vehicles.filter((vehicle) => vehicle.data_mode === 'LIVE').length} live</b></div>

      {canManageGps && <form className="vehicle-registration" onSubmit={submit}>
        <div><p className="eyebrow">ONBOARD A REAL VEHICLE</p><h2>Register this GPS device</h2><span>Uses this browser's current coordinates. Permission is requested only when you submit.</span></div>
        <label><span>Registration number</span><input required minLength={3} value={registration} onChange={(event) => setRegistration(event.target.value)} placeholder="AS-01-AB-1234" /></label>
        <label><span>Vehicle type</span><select value={vehicleClass} onChange={(event) => setVehicleClass(event.target.value)}><option value="GENERAL_TRUCK">General truck</option><option value="REFRIGERATED_TRUCK">Refrigerated truck</option><option value="RELIEF_TRUCK">Relief truck</option><option value="AMBULANCE">Ambulance</option></select></label>
        <label><span>Delivery assignment</span><select value={deliveryId} onChange={(event) => setDeliveryId(event.target.value)}><option value="">Unassigned</option>{deliveries.filter((delivery) => delivery.vehicle_id === 'UNASSIGNED').map((delivery) => <option key={delivery.id} value={delivery.id}>{delivery.id} · {delivery.destination_name}</option>)}</select></label>
        <button className="primary" disabled={busy || !registration.trim()}><Satellite size={16} />{busy && updatingVehicleId === null ? 'Reading GPS…' : 'Register with live GPS'}</button>
      </form>}

      {notice && <div className="fleet-notice"><Radio size={15} />{notice}</div>}

      {vehicles.length === 0 ? <div className="empty-fleet"><Satellite size={30} /><h2>No GPS vehicles connected</h2><p>Register this device above, or have an AIS-140/GPS gateway send positions to <code>POST /api/v1/vehicles/:vehicle_id/positions</code>. The map intentionally stays empty until genuine telemetry arrives.</p></div> : <div className="fleet-grid">
        {vehicles.map((vehicle) => {
          const delivery = deliveries.find((item) => item.id === vehicle.active_delivery_id)
          const tracking = telemetry.find((item) => item.vehicle_id === vehicle.id)
          return <article className="fleet-card" key={vehicle.id}>
            <div className="fleet-card-head"><div className="fleet-icon"><Truck size={21} /></div><div><span>{vehicle.id}</span><h2>{vehicle.registration}</h2><p>{vehicle.vehicle_class.replaceAll('_', ' ')}{vehicle.driver_name ? ` · ${vehicle.driver_name}` : ''}</p></div><b className={`gps-state ${(tracking?.motion_state ?? vehicle.gps_freshness).toLowerCase()}`}>{tracking?.motion_state ?? vehicle.gps_freshness}</b></div>
            <div className="fleet-metrics"><div><Gauge size={16} /><span>Speed</span><strong>{Math.round(vehicle.speed_kph)} km/h</strong></div><div><Route size={16} /><span>Route deviation</span><strong>{tracking?.route_deviation_km === null || tracking?.route_deviation_km === undefined ? 'Not assigned' : `${tracking.route_deviation_km} km`}</strong></div><div><Clock3 size={16} /><span>GPS age</span><strong>{tracking ? `${tracking.gps_age_seconds}s` : 'Unknown'}</strong></div></div>
            {tracking && (tracking.on_planned_route === false || tracking.motion_state === 'STOPPED' || tracking.motion_state === 'STALE') && <div className="fleet-warning"><AlertTriangle size={14} /><span>{tracking.on_planned_route === false ? 'Vehicle is outside the assigned route corridor.' : tracking.motion_state === 'STOPPED' ? `Vehicle stopped for ${tracking.stationary_minutes} minutes.` : 'GPS feed is stale.'}</span></div>}
            <dl><div><dt>Telemetry source</dt><dd>{vehicle.source}</dd></div><div><dt>Track points</dt><dd>{tracking?.position_count ?? 1}</dd></div><div><dt>Last position</dt><dd>{timeLabel(vehicle.last_position_at)}</dd></div><div><dt>Accuracy</dt><dd>{vehicle.position_accuracy_m !== null ? `${Math.round(vehicle.position_accuracy_m)} m` : 'Not supplied'}</dd></div><div><dt>Coordinates</dt><dd>{vehicle.latitude.toFixed(4)}, {vehicle.longitude.toFixed(4)}</dd></div><div><dt>Assigned route</dt><dd>{tracking?.expected_route_id ?? 'None'}</dd></div></dl>
            <div className="fleet-assignment"><span>ACTIVE ASSIGNMENT</span>{delivery ? <><strong>{delivery.cargo_description}</strong><small>{delivery.id} · {delivery.destination_name}</small><div className="progress-track"><i style={{ width: `${delivery.progress_percent}%` }} /></div><small>{delivery.progress_percent}% complete · {delivery.tracking_status.replaceAll('_', ' ')}</small>{tracking && <small>Telemetry-predicted additional delay: {tracking.estimated_delivery_delay_minutes} min</small>}</> : <strong>No delivery assigned</strong>}</div>
            <div className="fleet-actions"><button className="secondary" onClick={onViewMap}><MapPinned size={15} /> Locate on map</button>{canManageGps && <button className="secondary" onClick={() => onShareGps(vehicle.id)} disabled={busy}><Satellite size={15} />{updatingVehicleId === vehicle.id ? 'Reading GPS…' : 'Share current GPS'}</button>}</div>
          </article>
        })}
      </div>}
    </section>
  )
}
