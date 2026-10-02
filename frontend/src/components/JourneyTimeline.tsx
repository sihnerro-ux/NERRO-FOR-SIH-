import type { Delivery } from '../types/api'

export function JourneyTimeline({ delivery }: { delivery: Delivery }) {
  return <details style={{ gridColumn: '1 / -1', padding: 16 }}>
    <summary>Journey timeline · {delivery.status.replaceAll('_', ' ')} · {delivery.instruction_status.toLowerCase()}</summary>
    {!delivery.journey_timeline?.length ? <p>No journey events recorded yet.</p> : <ol>{delivery.journey_timeline.map(event => <li key={event.id} style={{ margin: '10px 0' }}>
      <strong>{event.event.replaceAll('_', ' ')}</strong><br />
      <small>{new Date(event.at).toLocaleString('en-IN')} · {event.actor} · {event.status} · {event.instruction}</small>
    </li>)}</ol>}
  </details>
}
