import { AlertTriangle, CheckCircle2, Clock3, MapPin, ShieldAlert, XCircle } from 'lucide-react'
import type { Incident } from '../types/api'
import { EvidenceImage } from './EvidenceImage'

interface Props {
  incidents: Incident[]
  isReviewing: boolean
  onReview: (incidentId: string, decision: 'CONFIRM' | 'DOWNGRADE' | 'REJECT') => void
}

export function IncidentReviewView({ incidents, isReviewing, onReview }: Props) {
  const awaiting = incidents.filter((incident) => incident.verification === 'UNVERIFIED')
  return <section className="incident-review-view">
    <div className="review-summary-grid">
      <article><Clock3 size={18} /><span>Awaiting verification</span><strong>{awaiting.length}</strong></article>
      <article><CheckCircle2 size={18} /><span>Verified reports</span><strong>{incidents.filter((incident) => incident.verification.includes('VERIFIED')).length}</strong></article>
      <article><ShieldAlert size={18} /><span>Critical reports</span><strong>{incidents.filter((incident) => incident.severity === 'CRITICAL' && incident.verification !== 'REJECTED').length}</strong></article>
    </div>
    <article className="incident-review-panel">
      <div className="module-card-head"><div><p className="eyebrow">AUTHORITY WORK QUEUE</p><h2>Field reports requiring a decision</h2><p>A report remains evidence only until an authorized reviewer confirms or downgrades its accessibility impact.</p></div></div>
      {awaiting.length === 0 ? <div className="review-empty"><CheckCircle2 size={27} /><strong>No reports awaiting review</strong><span>New field submissions will appear here automatically.</span></div> : <div className="authority-review-list">{awaiting.map((incident) => {
        const context = incident.context_snapshot as { state?: string; district?: string; weather?: { rainfall_mm_24h?: number; mode?: string }; ml_assessment?: { risk_probability?: number; risk_band?: string }; nearest_road?: { name?: string; distance_km?: number } }
        return <section key={incident.id} className="authority-review-card">
          <div className="authority-review-main">
            <div className="authority-review-title"><span className={`severity-dot ${incident.severity.toLowerCase()}`} /><div><strong>{incident.incident_type.replaceAll('_', ' ')}</strong><small>{incident.id} · {incident.severity}</small></div></div>
            <p>{incident.description}</p>
            <div className="authority-location"><MapPin size={13} /><span>{context.district || 'Location pending'}{context.state ? `, ${context.state}` : ''} · {incident.location.coordinates[1].toFixed(5)}, {incident.location.coordinates[0].toFixed(5)}</span></div>
            {incident.photo_data_url && <EvidenceImage className="review-evidence-photo" source={incident.photo_data_url} />}
          </div>
          <div className="authority-context">
            <div><span>Reported accessibility</span><strong>{incident.reported_accessibility.replaceAll('_', ' ')}</strong></div>
            <div><span>Nearest road</span><strong>{context.nearest_road?.name ?? incident.matched_segment_id ?? 'Unmatched'}</strong><small>{context.nearest_road?.distance_km !== undefined ? `${context.nearest_road.distance_km} km away` : 'No distance context'}</small></div>
            <div><span>Weather</span><strong>{context.weather?.rainfall_mm_24h !== undefined ? `${context.weather.rainfall_mm_24h} mm/24h` : 'Not enriched'}</strong><small>{context.weather?.mode ?? 'UNAVAILABLE'}</small></div>
            <div><span>ML advisory</span><strong>{context.ml_assessment?.risk_probability !== undefined ? `${Math.round(context.ml_assessment.risk_probability * 100)}% · ${context.ml_assessment.risk_band}` : 'Not enriched'}</strong><small>Advisory only</small></div>
          </div>
          <div className="authority-actions">
            <button className="confirm" disabled={isReviewing} onClick={() => onReview(incident.id, 'CONFIRM')}><CheckCircle2 size={14} /> Confirm impact</button>
            <button disabled={isReviewing} onClick={() => onReview(incident.id, 'DOWNGRADE')}><AlertTriangle size={14} /> Mark caution</button>
            <button className="reject" disabled={isReviewing} onClick={() => onReview(incident.id, 'REJECT')}><XCircle size={14} /> Reject report</button>
          </div>
        </section>
      })}</div>}
    </article>
  </section>
}
