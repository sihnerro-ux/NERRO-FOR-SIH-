import { api } from './api'

export interface OperationsEvent {
  type: 'CONNECTED' | 'FIELD_REPORT_SUBMITTED' | 'FIELD_REPORT_REVIEWED' | 'GPS_POSITION_RECEIVED' | 'VEHICLE_REGISTERED' | 'DELIVERY_DISPATCHED' | 'DELIVERY_VEHICLE_ASSIGNED' | 'WEATHER_REFRESHED'
  changed_entities?: string[]
  actor?: string
  district?: string | null
  message?: string
  occurred_at: string
}

export type StreamStatus = 'CONNECTING' | 'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED'

export function connectOperationsStream(onEvent: (event: OperationsEvent) => void, onStatus: (status: StreamStatus) => void) {
  let socket: WebSocket | null = null
  let reconnectTimer: number | null = null
  let heartbeat: number | null = null
  let stopped = false
  let attempt = 0

  const connect = () => {
    const token = api.accessToken()
    if (!token || stopped) { onStatus('DISCONNECTED'); return }
    onStatus(attempt === 0 ? 'CONNECTING' : 'RECONNECTING')
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/ws/operations?token=${encodeURIComponent(token)}`)
    socket.onopen = () => {
      attempt = 0
      onStatus('CONNECTED')
      heartbeat = window.setInterval(() => {
        if (socket?.readyState === WebSocket.OPEN) socket.send('ping')
      }, 25000)
    }
    socket.onmessage = (message) => {
      try { onEvent(JSON.parse(message.data) as OperationsEvent) } catch { /* Ignore malformed provider frames. */ }
    }
    socket.onclose = () => {
      if (heartbeat !== null) window.clearInterval(heartbeat)
      heartbeat = null
      if (stopped) { onStatus('DISCONNECTED'); return }
      attempt += 1
      onStatus('RECONNECTING')
      reconnectTimer = window.setTimeout(connect, Math.min(15000, 1000 * 2 ** Math.min(attempt, 4)))
    }
  }

  connect()
  return () => {
    stopped = true
    if (reconnectTimer !== null) window.clearTimeout(reconnectTimer)
    if (heartbeat !== null) window.clearInterval(heartbeat)
    socket?.close()
    onStatus('DISCONNECTED')
  }
}
