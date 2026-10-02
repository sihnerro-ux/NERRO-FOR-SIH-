import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, Clock3, LocateFixed, MapPinned, Navigation, PackageCheck, Route, Search, ShieldCheck, X } from 'lucide-react'
import { api } from '../services/api'
import type { DeliveryCreateRequest, LocationSearchResult, RouteCandidate, RouteLocation, RoutePlanResponse, RoutePreference, Vehicle } from '../types/api'

const preferenceOptions: Array<{ value: RoutePreference; title: string; detail: string }> = [
  { value: 'SAFETY_FIRST', title: 'Safety first', detail: 'Avoid disruption exposure' },
  { value: 'BALANCED', title: 'Balanced', detail: 'Time and risk together' },
  { value: 'FASTEST_FEASIBLE', title: 'Fastest', detail: 'Shortest feasible ETA' },
]

const PROCESSING_STAGES = [
  'Finding alternative road paths',
  'Reading live weather and terrain',
  'Matching field reports and road updates',
  'Running active prototype ML risk and delay prediction',
  'Filtering closures and ranking the best route',
]

const QUICK_LOCATIONS: RouteLocation[] = [
  { label: 'Guwahati, Assam', latitude: 26.1445, longitude: 91.7362 },
  { label: 'Dibrugarh, Assam', latitude: 27.4728, longitude: 94.9120 },
  { label: 'Silchar, Assam', latitude: 24.8333, longitude: 92.7789 },
  { label: 'Tezpur, Assam', latitude: 26.6528, longitude: 92.7926 },
  { label: 'Jorhat, Assam', latitude: 26.7509, longitude: 94.2037 },
  { label: 'Itanagar, Arunachal Pradesh', latitude: 27.0844, longitude: 93.6053 },
  { label: 'Tawang, Arunachal Pradesh', latitude: 27.5861, longitude: 91.8594 },
  { label: 'Pasighat, Arunachal Pradesh', latitude: 28.0661, longitude: 95.3260 },
  { label: 'Shillong, Meghalaya', latitude: 25.5788, longitude: 91.8933 },
  { label: 'Tura, Meghalaya', latitude: 25.5142, longitude: 90.2024 },
  { label: 'Imphal, Manipur', latitude: 24.8170, longitude: 93.9368 },
  { label: 'Churachandpur, Manipur', latitude: 24.3333, longitude: 93.6833 },
  { label: 'Aizawl, Mizoram', latitude: 23.7271, longitude: 92.7176 },
  { label: 'Lunglei, Mizoram', latitude: 22.8870, longitude: 92.7477 },
  { label: 'Kohima, Nagaland', latitude: 25.6751, longitude: 94.1086 },
  { label: 'Dimapur, Nagaland', latitude: 25.9091, longitude: 93.7266 },
  { label: 'Gangtok, Sikkim', latitude: 27.3389, longitude: 88.6065 },
  { label: 'Namchi, Sikkim', latitude: 27.1667, longitude: 88.3500 },
  { label: 'Agartala, Tripura', latitude: 23.8315, longitude: 91.2868 },
  { label: 'Dharmanagar, Tripura', latitude: 24.3786, longitude: 92.1783 },
]

function duration(minutes: number) {
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
}

interface LocationPickerProps {
  kind: 'FROM' | 'TO'
  selected: RouteLocation | null
  onSelect: (location: RouteLocation | null) => void
}

function LocationPicker({ kind, selected, onSelect }: LocationPickerProps) {
  const [query, setQuery] = useState(selected?.label ?? '')
  const [results, setResults] = useState<LocationSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [locating, setLocating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const choose = (location: RouteLocation) => {
    onSelect(location)
    setQuery(location.label)
    setResults([])
    setError(null)
  }

  const useCurrentLocation = () => {
    if (!navigator.geolocation) { setError('Location access is not supported by this browser.'); return }
    setLocating(true)
    setError(null)
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const insideNer = coords.latitude >= 21 && coords.latitude <= 30.5 && coords.longitude >= 87.5 && coords.longitude <= 98.5
        if (!insideNer) {
          setError('Your current position is outside the NER operating area.')
        } else {
          choose({ label: `My live location (±${Math.round(coords.accuracy)} m)`, latitude: coords.latitude, longitude: coords.longitude })
        }
        setLocating(false)
      },
      () => { setError('Location permission was denied or GPS is unavailable.'); setLocating(false) },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 },
    )
  }

  const search = async () => {
    if (query.trim().length < 2) { setError('Enter at least two characters.'); return }
    setLoading(true)
    setError(null)
    try {
      const matches = await api.searchLocations(query)
      setResults(matches)
      if (matches.length === 0) setError('No matching location found inside the eight NER states.')
    } catch {
      setError('Location search is temporarily unavailable.')
    } finally {
      setLoading(false)
    }
  }

  return <div className="location-picker">
    <label><MapPinned size={16} /><span>{kind}</span><div className="location-search-box"><input value={query} autoComplete="off" onChange={(event) => { setQuery(event.target.value); onSelect(null); setResults([]) }} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); void search() } }} placeholder={kind === 'FROM' ? 'Search any origin in NER' : 'Search any destination in NER'} /><button type="button" onClick={() => void search()} disabled={loading} aria-label={`Search ${kind.toLowerCase()} location`}><Search size={15} /></button></div></label>
    <div className="location-shortcuts">
      <select aria-label={`Choose quick ${kind.toLowerCase()} location`} value="" onChange={(event) => { const location = QUICK_LOCATIONS[Number(event.target.value)]; if (location) choose(location) }}>
        <option value="">Choose from 20 NER locations</option>
        {QUICK_LOCATIONS.map((location, index) => <option key={location.label} value={index}>{location.label}</option>)}
      </select>
      <button type="button" onClick={useCurrentLocation} disabled={locating}><LocateFixed size={13} />{locating ? 'Locating…' : 'Use my location'}</button>
    </div>
    {selected && <div className="selected-location"><CheckCircle2 size={13} /><span>{selected.label}</span><small>{selected.latitude.toFixed(4)}, {selected.longitude.toFixed(4)}</small></div>}
    {error && <p className="location-error">{error}</p>}
    {results.length > 0 && <div className="location-results">{results.map((result) => <button type="button" key={result.id} onClick={() => choose(result)}><strong>{result.label.split(',').slice(0, 2).join(',')}</strong><span>{result.district ? `${result.district}, ` : ''}{result.state}</span></button>)}</div>}
  </div>
}

interface Props {
  isLoading: boolean
  result?: RoutePlanResponse
  error?: Error | null
  preference: RoutePreference
  selectedRouteId: string | null
  onPreference: (preference: RoutePreference) => void
  onPlan: (source: RouteLocation, destination: RouteLocation) => void
  onSelectRoute: (route: RouteCandidate) => void
  vehicles: Vehicle[]
  canDispatch: boolean
  isDispatching: boolean
  dispatchError?: Error | null
  onDispatch: (request: DeliveryCreateRequest) => void
  onClose: () => void
}

export function RoutePlannerPanel({ isLoading, result, error, preference, selectedRouteId, onPreference, onPlan, onSelectRoute, vehicles, canDispatch, isDispatching, dispatchError, onDispatch, onClose }: Props) {
  const [origin, setOrigin] = useState<RouteLocation | null>(null)
  const [destination, setDestination] = useState<RouteLocation | null>(null)
  const [hasCalculated, setHasCalculated] = useState(false)
  const [showAlternatives, setShowAlternatives] = useState(false)
  const [activeProcessingStep, setActiveProcessingStep] = useState(0)
  const [cargoType, setCargoType] = useState('EMERGENCY_MEDICINES')
  const [cargoDescription, setCargoDescription] = useState('Critical medicines and medical supplies')
  const [priority, setPriority] = useState<DeliveryCreateRequest['priority']>('CRITICAL')
  const [vehicleId, setVehicleId] = useState('')

  useEffect(() => {
    if (!isLoading) return
    setActiveProcessingStep(0)
    const timer = window.setInterval(() => setActiveProcessingStep((step) => Math.min(step + 1, PROCESSING_STAGES.length - 1)), 850)
    return () => window.clearInterval(timer)
  }, [isLoading])

  const changeOrigin = (location: RouteLocation | null) => {
    setOrigin(location)
    setHasCalculated(false)
  }

  const changeDestination = (location: RouteLocation | null) => {
    setDestination(location)
    setHasCalculated(false)
  }

  const calculate = () => {
    if (!origin || !destination) return
    setShowAlternatives(false)
    setHasCalculated(true)
    onPlan(origin, destination)
  }

  const changePreference = (nextPreference: RoutePreference) => {
    onPreference(nextPreference)
    setHasCalculated(false)
  }

  const bestRoute = result?.routes.find((route) => route.id === result.recommended_route_id) ?? result?.routes[0]
  const visibleRoutes = showAlternatives ? result?.routes ?? [] : bestRoute ? [bestRoute] : []
  const selectedRoute = result?.routes.find((route) => route.id === selectedRouteId) ?? null
  const availableVehicles = vehicles.filter((vehicle) => !vehicle.active_delivery_id)

  return (
    <section className="planner-panel" aria-label="Emergency route planner">
      <div className="planner-heading">
        <div><p className="eyebrow">NER-WIDE RISK-AWARE ROUTING</p><h2>Where should the delivery go?</h2><p>Select both locations first. No route is calculated until you click the button.</p></div>
        <button className="planner-close" onClick={onClose} aria-label="Close route planner"><X size={18} /></button>
      </div>
      <div className="route-location-search">
        <LocationPicker kind="FROM" selected={origin} onSelect={changeOrigin} />
        <i><Navigation size={16} /></i>
        <LocationPicker kind="TO" selected={destination} onSelect={changeDestination} />
        <div className="cargo-chip"><ShieldCheck size={15} /><span>Critical medicine</span></div>
      </div>
      <div className="geocoder-note">Use device GPS, choose one of 20 quick locations, or search any place in the eight North Eastern states.</div>
      <div className="preference-row">
        {preferenceOptions.map((option) => (
          <button key={option.value} className={`preference ${preference === option.value ? 'selected' : ''}`} onClick={() => changePreference(option.value)}>
            <strong>{option.title}</strong><span>{option.detail}</span>
          </button>
        ))}
        <button className="primary calculate-route" onClick={calculate} disabled={isLoading || !origin || !destination}><Route size={16} />{isLoading ? 'Assessing routes…' : 'Calculate best routes'}</button>
      </div>

      {hasCalculated && isLoading && <section className="route-processing" aria-live="polite">
        <div className="processing-title"><span className="processing-spinner" /><div><strong>Building a risk-aware route</strong><small>Reading the latest operational inputs before selecting a path.</small></div></div>
        <ol>{PROCESSING_STAGES.map((stage, index) => <li className={index < activeProcessingStep ? 'completed' : index === activeProcessingStep ? 'active' : 'pending'} key={stage}><span>{index < activeProcessingStep ? '✓' : index + 1}</span><b>{stage}</b></li>)}</ol>
      </section>}

      {hasCalculated && !isLoading && result && result.processing_steps.length > 0 && <section className="route-processing completed-trace">
        <div className="processing-title"><CheckCircle2 size={18} /><div><strong>Route intelligence completed</strong><small>These are the inputs actually processed by the backend.</small></div></div>
        <ol>{result.processing_steps.map((step) => <li className={step.status === 'COMPLETED' ? 'completed' : 'degraded'} key={step.key}><span>{step.status === 'COMPLETED' ? '✓' : '!'}</span><div><b>{step.label}</b><small>{step.detail}</small></div></li>)}</ol>
      </section>}

      {hasCalculated && error && <div className="planner-error"><AlertTriangle size={17} />Unable to calculate a route. Check the locations or live feeds, then try again.</div>}
      {hasCalculated && result?.status === 'NO_FEASIBLE_ROUTE' && (
        <div className="no-route"><AlertTriangle size={21} /><div><strong>No currently accessible road route</strong><p>{result.warnings.at(-1)} {result.excluded_blocked_segments.length > 0 && `Blocked: ${result.excluded_blocked_segments.join(', ')}.`}</p></div></div>
      )}
      {hasCalculated && result?.status === 'ROUTES_AVAILABLE' && (
        <>
          <div className="planner-results-head"><span><CheckCircle2 size={15} /> Best route selected from {result.routes.length} option{result.routes.length === 1 ? '' : 's'} <b className={`routing-source ${result.routing_status.toLowerCase()}`}>{result.routing_status === 'LIVE' ? 'LIVE INPUTS + PROTOTYPE ML' : 'CURATED FALLBACK'}</b></span><div><small>Weather, field reports, road status and ML risk included.</small>{result.routes.length > 1 && <button className="alternatives-toggle" onClick={() => setShowAlternatives((shown) => !shown)}>{showAlternatives ? 'Show best only' : `View ${result.routes.length - 1} alternative${result.routes.length > 2 ? 's' : ''}`}</button>}</div></div>
          <div className={`route-results ${showAlternatives ? '' : 'best-only'}`}>
            {visibleRoutes.map((route) => (
              <button className={`route-option ${selectedRouteId === route.id ? 'route-selected' : ''}`} key={route.id} onClick={() => onSelectRoute(route)}>
                <div className="route-option-top"><span className={`risk-badge ${route.risk_band.toLowerCase()}`}>{route.label}</span><span>{route.risk_score}% predicted risk</span></div>
                <div className="route-metrics"><div><Route size={14} /><strong>{route.distance_km} km</strong><span>Distance</span></div><div><Clock3 size={14} /><strong>{duration(route.eta_minutes)}</strong><span>ETA</span></div><div><AlertTriangle size={14} /><strong>+{route.predicted_delay_minutes}m</strong><span>ML delay</span></div></div>
                <div className="route-intelligence"><div><span>ML risk</span><strong>{route.ml_risk_probability === null ? 'Unavailable' : `${Math.round(route.ml_risk_probability * 100)}%`}</strong></div><div><span>Live rainfall</span><strong>{route.live_rainfall_mm_24h === null ? 'Unavailable' : `${Math.round(route.live_rainfall_mm_24h)} mm`}</strong></div><div><span>Data confidence</span><strong>{route.risk_coverage_percent}%</strong></div></div>
                <p className="route-path">{route.path.join(' → ')}</p><small>{route.risk_factors.join(' · ')}</small>
              </button>
            ))}
          </div>
          {canDispatch && selectedRoute && origin && destination && <section className="dispatch-panel">
            <div><p className="eyebrow">CREATE TRACKED DELIVERY</p><h3>Dispatch this route</h3><small>The selected route, risk assessment and geometry will be stored with the delivery.</small></div>
            <div className="dispatch-fields">
              <label>Cargo type<select value={cargoType} onChange={(event) => setCargoType(event.target.value)}><option value="EMERGENCY_MEDICINES">Medicines</option><option value="FOOD_SUPPLIES">Food supplies</option><option value="AGRICULTURAL_PRODUCE">Agricultural produce</option><option value="CONSTRUCTION_MATERIALS">Construction materials</option><option value="RELIEF_SUPPLIES">Relief supplies</option></select></label>
              <label>Priority<select value={priority} onChange={(event) => setPriority(event.target.value as DeliveryCreateRequest['priority'])}><option value="CRITICAL">Critical</option><option value="HIGH">High</option><option value="NORMAL">Normal</option></select></label>
              <label>GPS vehicle<select value={vehicleId} onChange={(event) => setVehicleId(event.target.value)}><option value="">Assign later</option>{availableVehicles.map((vehicle) => <option value={vehicle.id} key={vehicle.id}>{vehicle.registration} · {vehicle.vehicle_class.replaceAll('_', ' ')} · {vehicle.data_mode === 'LIVE' ? 'LIVE' : 'DEMO'}</option>)}</select></label>
              <label className="dispatch-description">Cargo description<input value={cargoDescription} minLength={3} maxLength={240} onChange={(event) => setCargoDescription(event.target.value)} /></label>
            </div>
            <div className="dispatch-actions"><span>{availableVehicles.length} unassigned registered vehicle{availableVehicles.length === 1 ? '' : 's'} available; demo GPS remains visibly labelled</span><button className="primary" disabled={isDispatching || cargoDescription.trim().length < 3} onClick={() => onDispatch({ cargo_type: cargoType, cargo_description: cargoDescription.trim(), priority, source: origin, destination, selected_route: selectedRoute, vehicle_id: vehicleId || null })}><PackageCheck size={16} />{isDispatching ? 'Creating delivery…' : vehicleId ? 'Dispatch and track' : 'Create unassigned delivery'}</button></div>
            {dispatchError && <div className="planner-error"><AlertTriangle size={16} />Dispatch failed. The vehicle or route may have changed; recalculate and try again.</div>}
          </section>}
        </>
      )}
    </section>
  )
}
