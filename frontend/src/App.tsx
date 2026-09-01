import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  AlertTriangle,
  Bell,
  Boxes,
  ChevronRight,
  CircleGauge,
  CloudRain,
  Map,
  MapPin,
  Menu,
  Navigation,
  PackageCheck,
  Radio,
  RefreshCw,
  Route,
  Search,
  ShieldAlert,
  Truck,
  Users,
} from 'lucide-react'
import { OperationsMap } from './components/OperationsMap'
import { api } from './services/api'
import type { RoadSegment } from './types/api'

const navItems = [
  { label: 'Overview', icon: CircleGauge, active: true },
  { label: 'Live map', icon: Map },
  { label: 'Route planner', icon: Route },
  { label: 'Deliveries', icon: Boxes },
  { label: 'Fleet', icon: Truck },
  { label: 'Incidents', icon: ShieldAlert },
  { label: 'Alerts', icon: Bell },
  { label: 'Analytics', icon: Activity },
  { label: 'Administration', icon: Users },
]

const metricCards = [
  { key: 'active_vehicles', label: 'Active vehicles', icon: Truck, tone: 'mint' },
  { key: 'critical_deliveries', label: 'Critical deliveries', icon: PackageCheck, tone: 'blue' },
  { key: 'blocked_segments', label: 'Blocked segments', icon: ShieldAlert, tone: 'red' },
  { key: 'high_risk_segments', label: 'High-risk segments', icon: AlertTriangle, tone: 'orange' },
  { key: 'delayed_deliveries', label: 'Delayed deliveries', icon: Activity, tone: 'amber' },
]

function timeLabel(value: string) {
  return new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

function App() {
  const queryClient = useQueryClient()
  const [selectedRoadId, setSelectedRoadId] = useState<string | null>('SEG-004')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const overviewQuery = useQuery({ queryKey: ['overview'], queryFn: api.overview })
  const mapQuery = useQuery({ queryKey: ['map-snapshot'], queryFn: api.mapSnapshot })

  const updateData = (payload: Awaited<ReturnType<typeof api.simulateHeavyRain>>) => {
    queryClient.setQueryData(['overview'], payload.overview)
    queryClient.setQueryData(['map-snapshot'], payload.map_snapshot)
  }

  const rainMutation = useMutation({ mutationFn: api.simulateHeavyRain, onSuccess: updateData })
  const resetMutation = useMutation({ mutationFn: api.resetSimulation, onSuccess: updateData })

  const selectedRoad: RoadSegment | undefined = useMemo(
    () => mapQuery.data?.road_segments.find((road) => road.id === selectedRoadId),
    [mapQuery.data, selectedRoadId],
  )

  const loading = overviewQuery.isLoading || mapQuery.isLoading
  const failed = overviewQuery.isError || mapQuery.isError

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><Navigation size={19} /></div>
          <div><strong>NER LOGISTICS</strong><span>INTELLIGENCE GRID</span></div>
        </div>
        <nav>
          <p className="nav-label">COMMAND CENTRE</p>
          {navItems.map(({ label, icon: Icon, active }) => (
            <button className={`nav-item ${active ? 'active' : ''}`} key={label}>
              <Icon size={18} /><span>{label}</span>{active && <span className="active-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="network-card"><Radio size={16} /><div><strong>Systems operational</strong><span>Simulated data · just now</span></div></div>
          <div className="profile"><div className="avatar">AK</div><div><strong>Arun Kumar</strong><span>Control room admin</span></div><ChevronRight size={16} /></div>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <button className="mobile-menu" onClick={() => setSidebarOpen(!sidebarOpen)}><Menu /></button>
          <div className="corridor"><MapPin size={16} /><span>Assam–Arunachal pilot corridor</span><ChevronRight size={15} /></div>
          <div className="top-actions">
            <label className="search"><Search size={17} /><input aria-label="Search" placeholder="Search vehicle, delivery or road" /></label>
            <span className="mode-badge"><span /> SIMULATED</span>
            <button className="icon-button"><Bell size={18} /><i /></button>
          </div>
        </header>

        <div className="page">
          <section className="page-heading">
            <div><p className="eyebrow">OPERATIONS OVERVIEW</p><h1>Good evening, Control Room</h1><p>Live accessibility and essential-supply movement across the pilot corridor.</p></div>
            <div className="heading-actions">
              <button className="secondary" onClick={() => resetMutation.mutate()} disabled={resetMutation.isPending}><RefreshCw size={16} /> Reset demo</button>
              <button className="primary"><Route size={16} /> Plan emergency route</button>
            </div>
          </section>

          {failed && <div className="error-banner"><AlertTriangle size={18} /><span>Backend unavailable. Start the FastAPI service on port 8000 and retry.</span></div>}
          {loading && <div className="loading-card">Loading operational picture…</div>}

          {overviewQuery.data && mapQuery.data && (
            <>
              <section className="metrics-grid">
                {metricCards.map(({ key, label, icon: Icon, tone }) => (
                  <article className="metric-card" key={key}>
                    <div className={`metric-icon ${tone}`}><Icon size={19} /></div>
                    <div><span>{label}</span><strong>{overviewQuery.data.metrics[key] ?? 0}</strong></div>
                    <small>Current corridor</small>
                  </article>
                ))}
              </section>

              <section className="operations-grid">
                <article className="map-card">
                  <div className="card-head">
                    <div><span className="live-dot" /> <strong>Operational map</strong><p>Guwahati → Tawang supply corridor</p></div>
                    <div className="legend"><span><i className="open" /> Open</span><span><i className="caution" /> Caution</span><span><i className="risk" /> High risk</span><span><i className="blocked" /> Blocked</span></div>
                  </div>
                  <div className="map-wrap">
                    <OperationsMap snapshot={mapQuery.data} selectedRoadId={selectedRoadId} onSelectRoad={setSelectedRoadId} />
                    {selectedRoad && (
                      <div className="road-inspector">
                        <div className="inspector-top"><span>{selectedRoad.id}</span><b className={`status status-${selectedRoad.risk_band.toLowerCase()}`}>{selectedRoad.accessibility.replace('_', ' ')}</b></div>
                        <h3>{selectedRoad.road_name}</h3>
                        <p>{selectedRoad.from_node} → {selectedRoad.to_node}</p>
                        <div className="risk-row"><div><span>Risk score</span><strong>{selectedRoad.risk_score}%</strong></div><div className="risk-track"><i style={{ width: `${selectedRoad.risk_score}%` }} /></div></div>
                        <dl><div><dt>Rainfall / 24h</dt><dd>{selectedRoad.rainfall_mm_24h} mm</dd></div><div><dt>Road condition</dt><dd>{selectedRoad.road_condition}</dd></div><div><dt>Confidence</dt><dd>{selectedRoad.confidence}%</dd></div></dl>
                        <small>{selectedRoad.source} · updated {timeLabel(selectedRoad.updated_at)}</small>
                      </div>
                    )}
                  </div>
                </article>

                <aside className="right-column">
                  <article className="panel alerts-panel">
                    <div className="panel-title"><div><span>ACTIVE ALERTS</span><h2>Needs attention</h2></div><b>{overviewQuery.data.critical_alerts.length}</b></div>
                    <div className="alert-list">
                      {overviewQuery.data.critical_alerts.map((alert) => (
                        <button className={`alert-row ${alert.severity.toLowerCase()}`} key={alert.id}>
                          <div className="alert-symbol">{alert.severity === 'CRITICAL' ? <ShieldAlert size={18} /> : <CloudRain size={18} />}</div>
                          <div><strong>{alert.title}</strong><p>{alert.message}</p><span>{timeLabel(alert.created_at)} · {alert.related_entity_id}</span></div>
                          <ChevronRight size={16} />
                        </button>
                      ))}
                    </div>
                    <button
                      className="rain-action"
                      onClick={() => rainMutation.mutate()}
                      disabled={rainMutation.isPending || overviewQuery.data.metrics.high_risk_segments > 0}
                    ><CloudRain size={17} />{overviewQuery.data.metrics.high_risk_segments > 0 ? 'Heavy rain event active' : 'Simulate heavy rainfall'}</button>
                  </article>

                  <article className="panel connectivity-panel">
                    <div className="panel-title"><div><span>CORRIDOR HEALTH</span><h2>Connectivity</h2></div><Navigation size={19} /></div>
                    {overviewQuery.data.connectivity.map((item) => (
                      <div className="connectivity-row" key={item.name}>
                        <div><strong>{item.name}</strong><span>{item.status}</span></div><b>{item.score}%</b>
                        <div className="connectivity-track"><i style={{ width: `${item.score}%` }} /></div>
                      </div>
                    ))}
                  </article>
                </aside>
              </section>

              <section className="deliveries-section">
                <div className="section-title"><div><p className="eyebrow">PRIORITY MOVEMENTS</p><h2>Essential deliveries</h2></div><button className="text-button">View all deliveries <ChevronRight size={16} /></button></div>
                <div className="delivery-grid">
                  {overviewQuery.data.priority_deliveries.map((delivery) => (
                    <article className="delivery-card" key={delivery.id}>
                      <div className="delivery-top"><span className={`priority ${delivery.priority.toLowerCase()}`}>{delivery.priority}</span><span className={`delivery-status ${delivery.status.toLowerCase().replace('_', '-')}`}>{delivery.status.replace('_', ' ')}</span></div>
                      <h3>{delivery.cargo_description}</h3><p>{delivery.id} · {delivery.vehicle_id}</p>
                      <div className="journey-line"><span>{delivery.source_name}</span><i /><span>{delivery.destination_name}</span></div>
                      <div className="progress-meta"><span>{delivery.progress_percent}% complete</span><span>ETA {timeLabel(delivery.current_eta)}</span></div>
                      <div className="progress-track"><i style={{ width: `${delivery.progress_percent}%` }} /></div>
                    </article>
                  ))}
                </div>
              </section>
            </>
          )}
        </div>
      </main>
    </div>
  )
}

export default App

