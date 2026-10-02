import test from 'node:test'
import assert from 'node:assert/strict'
import { gpsRejectionReason } from '../src/services/gpsPolicy.ts'

const now = 1800000000000
const fix = { timestamp: now, coords: { latitude: 26.1445, longitude: 91.7362, accuracy: 15 } }
test('accepts a fresh accurate device fix', () => assert.equal(gpsRejectionReason(fix, now), null))
test('rejects stale, future and non-finite timestamps', () => {
  for (const timestamp of [now - 60001, now + 10001, NaN]) {
    assert.ok(gpsRejectionReason({ ...fix, timestamp }, now))
  }
})
test('rejects inaccurate or malformed fixes', () => {
  for (const accuracy of [101, -1, Infinity, NaN]) {
    assert.ok(gpsRejectionReason({ ...fix, coords: { ...fix.coords, accuracy } }, now))
  }
  assert.ok(gpsRejectionReason({ ...fix, coords: { ...fix.coords, latitude: NaN } }, now))
})
test('does not silently relocate an out-of-NER device to demo coordinates', () => {
  const outside = { ...fix, coords: { ...fix.coords, latitude: 21.25, longitude: 81.63 } }
  assert.equal(gpsRejectionReason(outside, now), null) // Backend owns NER boundary enforcement.
  assert.equal(outside.coords.longitude, 81.63)
})
