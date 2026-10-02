import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../services/api'
import { gpsRejectionReason } from '../services/gpsPolicy'

/** Foreground-only, opt-in tracking. Coordinates never enter persistent browser storage. */
export function DriverLocationSharing({ vehicleId, deliveryId }: { vehicleId: string; deliveryId: string | null }) {
  const client = useQueryClient()
  const [sharing, setSharing] = useState(false)
  const [message, setMessage] = useState('Location sharing is off.')
  const [acceptedAt, setAcceptedAt] = useState<number | null>(null)
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    if (!sharing) return
    if (!window.isSecureContext || !navigator.geolocation) {
      setMessage('Phone GPS requires HTTPS (or localhost) and a supported browser.')
      setSharing(false)
      return
    }
    let disposed = false
    let pending: GeolocationPosition | null = null
    let inFlight = false
    let lastAccepted = 0
    const controller = new AbortController()
    setMessage('Waiting for GPS permission and an accurate position…')

    const flush = async () => {
      setNow(Date.now())
      if (disposed || inFlight || !pending) return
      if (!navigator.onLine) {
        setMessage('Offline: retaining only the latest position in memory. Reconnecting automatically.')
        return
      }
      const point = pending
      if (Date.now() - point.timestamp > 60000) {
        pending = null
        setMessage('GPS is stale. Waiting for a fresh position; old coordinates will not be resent.')
        return
      }
      inFlight = true
      try {
        await api.ingestVehiclePosition(vehicleId, {
          latitude: point.coords.latitude, longitude: point.coords.longitude,
          accuracy_m: point.coords.accuracy,
          speed_kph: Number.isFinite(point.coords.speed) ? Math.max(0, point.coords.speed! * 3.6) : 0,
          heading: Number.isFinite(point.coords.heading) ? ((point.coords.heading! % 360) + 360) % 360 : 0,
          recorded_at: new Date(point.timestamp).toISOString(), source: 'BROWSER_GPS',
        }, AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]))
        if (disposed) return
        lastAccepted = point.timestamp
        if (pending === point) pending = null
        setAcceptedAt(point.timestamp)
        setMessage(`Position accepted (accuracy ±${Math.round(point.coords.accuracy)} m).`)
        for (const key of ['driver-journey', 'map-snapshot', 'overview']) {
          void client.invalidateQueries({ queryKey: [key] })
        }
      } catch (error) {
        if (!disposed) {
          setMessage(error instanceof Error ? error.message : 'GPS upload failed; retrying with a fresh position.')
          // Keep retrying network failures, but do not loop on rejected positions.
          if (error instanceof ApiError && error.status < 500 && pending === point) pending = null
          if (error instanceof ApiError && (error.status === 401 || error.status === 403)) setSharing(false)
        }
      } finally { inFlight = false }
    }
    const watch = navigator.geolocation.watchPosition(point => {
      if (disposed || point.timestamp <= lastAccepted) return
      const rejection = gpsRejectionReason(point)
      if (rejection) {
        setMessage(rejection)
        return
      }
      if (!pending || point.timestamp > pending.timestamp) pending = point
    }, error => {
      setMessage(error.code === 1 ? 'GPS permission denied. Enable it in browser settings, then start sharing again.' : 'GPS unavailable. Waiting for the device to recover.')
      if (error.code === 1) setSharing(false)
    }, { enableHighAccuracy: true, maximumAge: 0, timeout: 20000 })
    const timer = window.setInterval(() => { void flush() }, 10000)
    const reconnect = () => { void flush() }
    window.addEventListener('online', reconnect)
    return () => {
      disposed = true
      navigator.geolocation.clearWatch(watch)
      window.clearInterval(timer)
      window.removeEventListener('online', reconnect)
      controller.abort()
      pending = null
    }
  }, [sharing, vehicleId, deliveryId, client])

  return <article className="driver-route-card">
    <div className="driver-route-head"><div><h2>Phone location sharing</h2>
      <p>Opt in to send GPS updates every 10 seconds while this workspace is open. Keep the screen awake. Background tracking is not guaranteed.</p>
    </div><button className="secondary" onClick={() => {
      setSharing(value => !value)
      if (sharing) setMessage('Location sharing stopped. No new positions will be collected.')
    }}>{sharing ? 'Stop sharing GPS' : 'Start sharing GPS'}</button></div>
    <p role="status">{sharing ? 'SHARING ENABLED — ' : 'OFF — '}{message}</p>
    {acceptedAt && <small>Last accepted GPS: {new Date(acceptedAt).toLocaleTimeString()} · {Math.max(0, Math.floor((now - acceptedAt) / 1000))}s old{sharing && now - acceptedAt > 60000 ? ' · STALE' : ''}</small>}
    <p>Sharing stops when you leave this workspace or sign out. Offline recovery keeps only the latest fix, not a historical track.</p>
  </article>
}
