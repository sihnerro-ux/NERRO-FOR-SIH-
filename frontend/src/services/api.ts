import type { AdministrationSnapshot, AlertFeed, Analytics, AuthUser, DeliveryCreateRequest, DeliveryCreateResponse, DriverJourneyResponse, FieldIncidentReportRequest, IncidentVerificationRequest, LocationContext, LocationSearchResult, MapSnapshot, OperationalDataImportRequest, OperationalDataImportResponse, Overview, RoutePlanRequest, RoutePlanResponse, SimulationResponse, TokenResponse, VehiclePositionResponse, VehicleRegistrationRequest, VehicleRegistrationResponse, WeatherRefreshResponse } from '../types/api'
import { clearOperationalSnapshots, loadOperationalSnapshot, saveOperationalSnapshot } from './offlineReference'

const TOKEN_KEY = 'ner-logistics-access-token'
const USER_KEY = 'ner-logistics-auth-user'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = window.localStorage.getItem(TOKEN_KEY)
  const headers = new Headers(options?.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(path, { ...options, headers })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const payload = await response.json() as { detail?: string | { message?: string } }
      if (typeof payload.detail === 'string') message = payload.detail
      else if (payload.detail?.message) message = payload.detail.message
    } catch { /* Preserve the status-based message for non-JSON errors. */ }
    throw new ApiError(message, response.status)
  }
  return response.json() as Promise<T>
}

async function requestBlob(path: string): Promise<Blob> {
  const token = window.localStorage.getItem(TOKEN_KEY)
  const headers = new Headers()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(path, { headers })
  if (!response.ok) throw new Error(`Evidence request failed (${response.status})`)
  return response.blob()
}

function storedUser(): AuthUser | null {
  try {
    const value = window.localStorage.getItem(USER_KEY)
    return value ? JSON.parse(value) as AuthUser : null
  } catch { return null }
}

async function operationalRequest<T>(path: string): Promise<T> {
  const user = storedUser()
  const cacheKey = `${user?.id ?? 'anonymous'}:${path}`
  try {
    const payload = await request<T>(path)
    if (user) void saveOperationalSnapshot(cacheKey, payload).catch(() => undefined)
    return payload
  } catch (error) {
    if (!user || navigator.onLine) throw error
    const cached = await loadOperationalSnapshot<T>(cacheKey)
    if (cached === null) throw error
    return cached
  }
}

export const api = {
  login: (username: string, password: string) => request<TokenResponse>('/api/v1/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }),
  }),
  me: () => request<AuthUser>('/api/v1/auth/me'),
  setSession: (session: TokenResponse) => {
    window.localStorage.setItem(TOKEN_KEY, session.access_token)
    window.localStorage.setItem(USER_KEY, JSON.stringify(session.user))
  },
  clearSession: () => {
    const user = storedUser()
    window.localStorage.removeItem(TOKEN_KEY)
    window.localStorage.removeItem(USER_KEY)
    if (user) void clearOperationalSnapshots(user.id).catch(() => undefined)
  },
  hasSession: () => Boolean(window.localStorage.getItem(TOKEN_KEY)),
  accessToken: () => window.localStorage.getItem(TOKEN_KEY),
  storedUser,
  overview: () => operationalRequest<Overview>('/api/v1/overview'),
  mapSnapshot: () => operationalRequest<MapSnapshot>('/api/v1/map/snapshot'),
  analytics: () => request<Analytics>('/api/v1/analytics'),
  alerts: (language: 'en' | 'hi') => request<AlertFeed>(`/api/v1/alerts?language=${language}`),
  administration: () => request<AdministrationSnapshot>('/api/v1/admin/overview'),
  importOperationalData: (payload: OperationalDataImportRequest) =>
    request<OperationalDataImportResponse>('/api/v1/admin/data/import', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    }),
  simulateHeavyRain: () =>
    request<SimulationResponse>('/api/v1/simulation/events/heavy-rain', { method: 'POST' }),
  simulationEvent: (eventName: string) =>
    request<SimulationResponse>(`/api/v1/simulation/events/${eventName}`, { method: 'POST' }),
  resetSimulation: () =>
    request<SimulationResponse>('/api/v1/simulation/reset', { method: 'POST' }),
  refreshWeather: () =>
    request<WeatherRefreshResponse>('/api/v1/weather/refresh', { method: 'POST' }),
  submitFieldReport: (payload: FieldIncidentReportRequest) =>
    request<SimulationResponse>('/api/v1/field-reports', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  verifyFieldReport: (incidentId: string, payload: IncidentVerificationRequest) =>
    request<SimulationResponse>(`/api/v1/incidents/${incidentId}/verification`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  acknowledgeAlert: (alertId: string) =>
    request<SimulationResponse>(`/api/v1/alerts/${alertId}/acknowledgement`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ acknowledged_by: 'Control room officer' }),
    }),
  planRoute: (payload: RoutePlanRequest) =>
    request<RoutePlanResponse>('/api/v1/routes/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  createDelivery: (payload: DeliveryCreateRequest) =>
    request<DeliveryCreateResponse>('/api/v1/deliveries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  assignDeliveryVehicle: (deliveryId: string, vehicleId: string) =>
    request<DeliveryCreateResponse>(`/api/v1/deliveries/${deliveryId}/vehicle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vehicle_id: vehicleId }),
    }),
  searchLocations: (query: string) =>
    request<LocationSearchResult[]>(`/api/v1/locations/search?q=${encodeURIComponent(query)}`),
  locationContext: (latitude: number, longitude: number) =>
    request<LocationContext>(`/api/v1/locations/context?latitude=${latitude}&longitude=${longitude}`),
  evidenceBlob: (path: string) => requestBlob(path),
  registerVehicle: (payload: VehicleRegistrationRequest) =>
    request<VehicleRegistrationResponse>('/api/v1/vehicles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  ingestVehiclePosition: (vehicleId: string, payload: { latitude: number; longitude: number; speed_kph: number; heading: number; accuracy_m: number | null; recorded_at: string; source: string }, signal?: AbortSignal) =>
    request<VehiclePositionResponse>(`/api/v1/vehicles/${vehicleId}/positions`, {
      method: 'POST',
      signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  driverJourney: () => request<DriverJourneyResponse>('/api/v1/driver/journey'),
  driverJourneyAction: (payload: { action: 'START_JOURNEY' | 'ACKNOWLEDGE_ROUTE' | 'COMPLETE_DELIVERY' | 'PAUSE_JOURNEY' | 'RESUME_JOURNEY' | 'REPORT_OBSTRUCTION'; instruction_updated_at?: string | null; description?: string }) =>
    request<DriverJourneyResponse>('/api/v1/driver/journey/actions', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    }),
}
