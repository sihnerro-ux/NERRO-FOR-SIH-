import { Bell, CheckCircle2, Languages, Radio, ShieldAlert } from 'lucide-react'
import { useState } from 'react'
import type { AlertFeed } from '../types/api'

interface Props { feed: AlertFeed; canAcknowledge: boolean; busy: boolean; onAcknowledge: (id: string) => void }

export function AlertsView({ feed, canAcknowledge, busy, onAcknowledge }: Props) {
  const [filter, setFilter] = useState<'ACTIVE' | 'ALL'>('ACTIVE')
  const items = feed.items.filter((alert) => filter === 'ALL' || !alert.acknowledged)
  return <section className="alerts-view">
    <div className="notification-strip"><Radio size={17} /><div><strong>Authenticated real-time notification channel</strong><span>Messages are generated from operational alerts and displayed in {feed.language === 'hi' ? 'Hindi' : 'English'}.</span></div><b><Languages size={14} /> {feed.language.toUpperCase()}</b></div>
    <div className="alert-toolbar"><div><p className="eyebrow">MULTILINGUAL NOTIFICATIONS</p><h2>Alert inbox</h2></div><div><button className={filter === 'ACTIVE' ? 'active' : ''} onClick={() => setFilter('ACTIVE')}>Active</button><button className={filter === 'ALL' ? 'active' : ''} onClick={() => setFilter('ALL')}>All history</button></div></div>
    <div className="alert-inbox">{items.length === 0 ? <div className="alert-empty"><CheckCircle2 size={26} /><strong>No active alerts</strong><span>New weather, incident, routing and GPS alerts will arrive through the live stream.</span></div> : items.map((alert) => <article key={alert.id} className={`alert-inbox-row ${alert.severity.toLowerCase()} ${alert.acknowledged ? 'acknowledged' : ''}`}><div className="alert-inbox-icon">{alert.severity === 'CRITICAL' ? <ShieldAlert size={18} /> : <Bell size={18} />}</div><div><strong>{alert.display_title}</strong><p>{alert.display_message}</p><span>{alert.alert_type.replaceAll('_', ' ')} · {alert.related_entity_type} {alert.related_entity_id} · {new Date(alert.created_at).toLocaleString('en-IN')}</span></div><div className="alert-channel"><small>{alert.channel.replaceAll('_', ' ')}</small>{alert.acknowledged ? <b>ACKNOWLEDGED</b> : canAcknowledge && <button disabled={busy} onClick={() => onAcknowledge(alert.id)}>Acknowledge</button>}</div></article>)}</div>
  </section>
}
