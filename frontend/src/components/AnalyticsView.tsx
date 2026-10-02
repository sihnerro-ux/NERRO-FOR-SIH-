import { Activity, CheckCircle2, CloudRain, Map, Radio, Route, ShieldAlert, Truck } from 'lucide-react'
import type { Analytics } from '../types/api'

const labels: Record<string, string> = {
  monitored_road_km: 'Monitored road km', active_deliveries: 'Active deliveries', arrived_deliveries: 'Arrived',
  average_delivery_progress: 'Average progress %', delayed_deliveries: 'Delayed', unassigned_deliveries: 'Unassigned', live_gps_vehicles: 'Live GPS vehicles',
}

export function AnalyticsView({ data }: { data: Analytics }) {
  const totalEvents = Math.max(1, ...data.event_trend.map((day) => day.field_reports + day.verification_actions + day.dispatches))
  return <section className="analytics-view" aria-label="Operational analytics">
    <div className="analytics-kpis">{Object.entries(data.summary).map(([key, value], index) => {
      const Icon = [Map, Truck, CheckCircle2, Activity, ShieldAlert, Route, Radio][index % 7]
      return <article key={key}><Icon size={17} /><span>{labels[key] ?? key.replaceAll('_', ' ')}</span><strong>{value}</strong></article>
    })}</div>

    <div className="analytics-grid">
      <article className="analytics-card state-connectivity"><div className="analytics-head"><div><p className="eyebrow">REGIONAL ACCESSIBILITY</p><h2>State connectivity</h2></div><Map size={19} /></div>
        <div className="state-list">{data.state_connectivity.map((state) => <div key={state.state}><div><strong>{state.state}</strong><span>{state.monitored_segments} corridors · {state.incidents} reports · {state.facilities} facilities</span></div><div className="analytics-bar"><i style={{ width: `${state.connectivity_score}%` }} /></div><b>{state.connectivity_score}%</b></div>)}</div>
      </article>

      <article className="analytics-card"><div className="analytics-head"><div><p className="eyebrow">DATA RELIABILITY</p><h2>Operational coverage</h2></div><Radio size={19} /></div>
        <div className="quality-list">{Object.entries(data.data_quality).map(([key, value]) => typeof value === 'number' ? <div key={key}><span>{key.replaceAll('_', ' ')}</span><div className="analytics-bar"><i style={{ width: `${Math.min(100, value)}%` }} /></div><b>{value}%</b></div> : <div className="quality-text" key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{value}</strong></div>)}</div>
      </article>

      <article className="analytics-card risk-table-card"><div className="analytics-head"><div><p className="eyebrow">PRIORITY MONITORING</p><h2>Highest-risk corridors</h2></div><ShieldAlert size={19} /></div>
        <div className="risk-table">{data.risk_corridors.map((road) => <div key={road.segment_id}><span><b>{road.segment_id}</b><strong>{road.road_name}</strong><small>{road.corridor}</small></span><span><small>Rain</small><b>{Math.round(road.rainfall_mm_24h)} mm</b></span><span><small>ML</small><b>{road.ml_risk_probability === null ? 'N/A' : `${Math.round(road.ml_risk_probability * 100)}%`}</b></span><span><small>Operational</small><b className={`risk-value ${road.accessibility.toLowerCase()}`}>{road.operational_risk}%</b></span></div>)}</div>
      </article>

      <article className="analytics-card"><div className="analytics-head"><div><p className="eyebrow">RECENT SYSTEM ACTIVITY</p><h2>Seven-day event flow</h2></div><Activity size={19} /></div>
        {data.event_trend.length === 0 ? <p className="analytics-empty">No operational events have been recorded yet.</p> : <div className="trend-list">{data.event_trend.map((day) => { const value = day.field_reports + day.verification_actions + day.dispatches; return <div key={day.date}><span>{new Date(`${day.date}T00:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}</span><div className="trend-bar"><i style={{ width: `${value / totalEvents * 100}%` }} /></div><b>{value}</b><small>{day.gps_updates} GPS pings</small></div> })}</div>}
        <div className="incident-breakdown"><h3>Incident types</h3>{Object.entries(data.incident_breakdown).map(([type, count]) => <span key={type}>{type.replaceAll('_', ' ')} <b>{count}</b></span>)}</div>
      </article>

      <article className="analytics-card district-card"><div className="analytics-head"><div><p className="eyebrow">LOCAL OPERATIONS</p><h2>District activity</h2></div><CloudRain size={19} /></div>
        <div className="district-grid">{data.district_activity.map((district) => <div key={district.district}><strong>{district.district}</strong><span>{district.incidents} reports</span><small>{district.unverified_incidents} awaiting review · {district.critical_incidents} critical · {district.facilities} facilities</small></div>)}</div>
      </article>
    </div>
  </section>
}
