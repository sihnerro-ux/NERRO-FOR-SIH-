import { AlertTriangle, Clock3, MapPinned, PackageCheck, Route, Truck } from 'lucide-react'
import { useState } from 'react'
import { JourneyTimeline } from './JourneyTimeline'
import type { Delivery, Vehicle } from '../types/api'

function timeLabel(value: string) {
  return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

interface Props {
  deliveries: Delivery[]
  vehicles: Vehicle[]
  canRoute: boolean
  onPlanRoute: () => void
  onViewMap: () => void
  canAssign: boolean
  assigningDeliveryId: string | null
  onAssignVehicle: (deliveryId: string, vehicleId: string) => void
}

export function DeliveriesView({ deliveries, vehicles, canRoute, onPlanRoute, onViewMap, canAssign, assigningDeliveryId, onAssignVehicle }: Props) {
  const [vehicleSelections, setVehicleSelections] = useState<Record<string, string>>({})
  const delayed = deliveries.filter((delivery) => delivery.delay_minutes > 0).length
  const critical = deliveries.filter((delivery) => delivery.priority === 'CRITICAL').length

  return (
    <section className="module-view" aria-label="Deliveries module">
      <div className="module-summary">
        <article><PackageCheck size={18} /><span>Active movements</span><strong>{deliveries.length}</strong></article>
        <article><AlertTriangle size={18} /><span>Delayed</span><strong>{delayed}</strong></article>
        <article><Truck size={18} /><span>Assigned vehicles</span><strong>{new Set(deliveries.map((item) => item.vehicle_id)).size}</strong></article>
        <article><Route size={18} /><span>Critical priority</span><strong>{critical}</strong></article>
      </div>

      <div className="module-table-card">
        <div className="module-card-head"><div><p className="eyebrow">DELIVERY CONTROL</p><h2>Essential-supply movements</h2><p>Assignments, current ETA, delay and route status share the same operational state as the control-room map.</p></div>{canRoute && <button className="primary" onClick={onPlanRoute}><Route size={16} /> Plan another route</button>}</div>
        <div className="delivery-table">
          {deliveries.map((delivery) => {
            const vehicle = vehicles.find((item) => item.id === delivery.vehicle_id)
            return <article className="delivery-row-full" key={delivery.id}>
              <div className="delivery-identity"><span className={`priority ${delivery.priority.toLowerCase()}`}>{delivery.priority}</span><div><strong>{delivery.cargo_description}</strong><small>{delivery.id} · {delivery.cargo_type.replaceAll('_', ' ')}</small></div></div>
              <div><span className="cell-label"><MapPinned size={13} /> Corridor</span><strong>{delivery.source_name}</strong><small>to {delivery.destination_name}</small></div>
              <div><span className="cell-label"><Truck size={13} /> Vehicle</span>{delivery.vehicle_id === 'UNASSIGNED' && canAssign ? <div className="inline-assignment"><select value={vehicleSelections[delivery.id] ?? ''} onChange={(event) => setVehicleSelections((current) => ({ ...current, [delivery.id]: event.target.value }))}><option value="">Choose GPS vehicle</option>{vehicles.filter((item) => !item.active_delivery_id).map((item) => <option key={item.id} value={item.id}>{item.registration} · {item.data_mode === 'LIVE' ? 'LIVE' : 'DEMO'}</option>)}</select><button disabled={!vehicleSelections[delivery.id] || assigningDeliveryId === delivery.id} onClick={() => onAssignVehicle(delivery.id, vehicleSelections[delivery.id])}>{assigningDeliveryId === delivery.id ? 'Assigning…' : 'Assign'}</button></div> : <><strong>{vehicle?.registration ?? delivery.vehicle_id}</strong><small>{vehicle?.gps_freshness ?? 'Unknown GPS'} · {vehicle?.data_mode ?? 'UNAVAILABLE'}</small></>}</div>
              <div><span className="cell-label"><Clock3 size={13} /> Current ETA</span><strong>{timeLabel(delivery.current_eta)}</strong><small className={delivery.delay_minutes > 0 ? 'delay-text' : ''}>{delivery.delay_minutes > 0 ? `+${delivery.delay_minutes} min delay` : 'On schedule'}</small></div>
              <div className="delivery-row-status"><span className={`delivery-status ${delivery.status.toLowerCase().replaceAll('_', '-')}`}>{delivery.status.replaceAll('_', ' ')}</span><div className="progress-track"><i style={{ width: `${delivery.progress_percent}%` }} /></div><small>{delivery.progress_percent}% complete · {delivery.tracking_status.replaceAll('_', ' ')}</small></div>
              <button className="secondary compact" onClick={onViewMap}><MapPinned size={14} /> View on map</button>
              <JourneyTimeline delivery={delivery} />
            </article>
          })}
        </div>
      </div>
    </section>
  )
}
