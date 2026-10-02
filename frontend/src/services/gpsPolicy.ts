export function gpsRejectionReason(point: Pick<GeolocationPosition, 'coords' | 'timestamp'>, now = Date.now()): string | null {
  if (!Number.isFinite(point.timestamp) || point.timestamp > now + 10000 || now - point.timestamp > 60000) {
    return 'GPS is stale or has an invalid timestamp. Waiting for a fresh position.'
  }
  if (!Number.isFinite(point.coords.latitude) || !Number.isFinite(point.coords.longitude)
    || Math.abs(point.coords.latitude) > 90 || Math.abs(point.coords.longitude) > 180) {
    return 'GPS returned invalid coordinates.'
  }
  if (!Number.isFinite(point.coords.accuracy) || point.coords.accuracy > 100 || point.coords.accuracy < 0) {
    return 'Weak GPS accuracy: waiting for a fix within 100 metres.'
  }
  return null
}
