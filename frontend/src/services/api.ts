import type { MapSnapshot, Overview, SimulationResponse } from '../types/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options)
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  overview: () => request<Overview>('/api/v1/overview'),
  mapSnapshot: () => request<MapSnapshot>('/api/v1/map/snapshot'),
  simulateHeavyRain: () =>
    request<SimulationResponse>('/api/v1/simulation/events/heavy-rain', { method: 'POST' }),
  resetSimulation: () =>
    request<SimulationResponse>('/api/v1/simulation/reset', { method: 'POST' }),
}

