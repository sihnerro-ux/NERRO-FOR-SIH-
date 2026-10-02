import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Activity, AlertTriangle, BrainCircuit, CheckCircle2, Database, FileCheck2, Radio, ShieldCheck, UploadCloud, Users } from 'lucide-react'
import { api } from '../services/api'
import type { AdministrationSnapshot, OperationalDataImportResponse } from '../types/api'

export function AdministrationView({ data }: { data: AdministrationSnapshot }) {
  const queryClient = useQueryClient()
  const [dataset, setDataset] = useState<File | null>(null)
  const [sourceName, setSourceName] = useState('')
  const [dataMode, setDataMode] = useState<'CACHED' | 'SIMULATED'>('CACHED')
  const [result, setResult] = useState<OperationalDataImportResponse | null>(null)
  const [importError, setImportError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const runImport = async (dryRun: boolean) => {
    if (!dataset || sourceName.trim().length < 3) return
    setBusy(true)
    setImportError(null)
    try {
      if (dataset.size > 5_000_000) throw new Error('The import file must be smaller than 5 MB.')
      const response = await api.importOperationalData({
        filename: dataset.name, source_name: sourceName.trim(), content: await dataset.text(), data_mode: dataMode, dry_run: dryRun,
      })
      setResult(response)
      if (!dryRun) {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['administration'] }),
          queryClient.invalidateQueries({ queryKey: ['map-snapshot'] }),
          queryClient.invalidateQueries({ queryKey: ['overview'] }),
          queryClient.invalidateQueries({ queryKey: ['analytics'] }),
        ])
      }
    } catch (error) {
      setResult(null)
      setImportError(error instanceof Error ? error.message : 'Dataset validation failed.')
    } finally {
      setBusy(false)
    }
  }

  return <section className='administration-view'>
    <div className='admin-summary'>
      <article><Users size={18} /><span>Active users</span><strong>{data.users.filter((user) => user.active).length}</strong></article>
      <article><Radio size={18} /><span>Integrations</span><strong>{data.sources.length}</strong></article>
      <article><Database size={18} /><span>Database</span><strong>{data.persistence.backend}</strong></article>
      <article><BrainCircuit size={18} /><span>ML advisory</span><strong>{data.ml.status}</strong></article>
    </div>

    <article className='admin-card data-import-card'>
      <div className='analytics-head'><div><p className='eyebrow'>CONTROLLED DATA INGESTION</p><h2>Import operational GeoJSON or CSV</h2><p>Validate the complete file before applying an atomic, source-attributed upsert.</p></div><UploadCloud size={20} /></div>
      <div className='data-import-form'>
        <label>Dataset file<input type='file' accept='.geojson,.json,.csv,application/geo+json,application/json,text/csv' onChange={(event) => { setDataset(event.target.files?.[0] ?? null); setResult(null); setImportError(null) }} /></label>
        <label>Authoritative source<input value={sourceName} placeholder='Department and dataset/version' maxLength={180} onChange={(event) => { setSourceName(event.target.value); setResult(null) }} /></label>
        <label>Data classification<select value={dataMode} onChange={(event) => { setDataMode(event.target.value as 'CACHED' | 'SIMULATED'); setResult(null) }}><option value='CACHED'>Cached external dataset</option><option value='SIMULATED'>Simulated prototype dataset</option></select></label>
        <button className='secondary' disabled={!dataset || sourceName.trim().length < 3 || busy} onClick={() => void runImport(true)}><FileCheck2 size={15} />{busy ? 'Validating…' : 'Validate preview'}</button>
        <button className='primary' disabled={result?.status !== 'PREVIEW_VALID' || busy} onClick={() => void runImport(false)}><UploadCloud size={15} />Apply validated import</button>
      </div>
      <p className='import-schema'>GeoJSON features require <code>entity_type</code> = <code>ROAD_SEGMENT</code> with LineString geometry, or <code>FACILITY</code> with Point geometry. CSV uses the same properties plus <code>geometry_json</code> for roads or <code>longitude</code>/<code>latitude</code> for facilities. Maximum 5 MB.</p>
      {importError && <div className='import-result error'><AlertTriangle size={16} /><span><strong>Import rejected</strong>{importError}</span></div>}
      {result && <div className={`import-result ${result.status === 'APPLIED' ? 'applied' : ''}`}><CheckCircle2 size={16} /><span><strong>{result.status === 'APPLIED' ? 'Dataset applied and audited' : 'Preview valid — no data changed'}</strong>{result.roads_received} roads and {result.facilities_received} facilities · {result.roads_created + result.facilities_created} new · {result.roads_updated + result.facilities_updated} updates</span></div>}
    </article>

    <div className='admin-grid'>
      <article className='admin-card'><div className='analytics-head'><div><p className='eyebrow'>ACCESS CONTROL</p><h2>Role assignments</h2></div><ShieldCheck size={19} /></div><div className='admin-users'>{data.users.map((user) => <div key={user.id}><span className={`user-state ${user.active ? 'active' : ''}`} /><span><strong>{user.display_name}</strong><small>{user.username}</small></span><b>{user.role.replaceAll('_', ' ')}</b><small>{user.district ?? 'NER-wide'}</small></div>)}</div></article>
      <article className='admin-card'><div className='analytics-head'><div><p className='eyebrow'>INTEGRATION HEALTH</p><h2>Operational data sources</h2></div><Radio size={19} /></div><div className='source-list'>{data.sources.map((source) => <div key={source.name}><CheckCircle2 size={14} /><span><strong>{source.name}</strong><small>{source.mode.replaceAll('_', ' ')}</small></span><b>{source.status}</b></div>)}</div></article>
      <article className='admin-card persistence-card'><div className='analytics-head'><div><p className='eyebrow'>SECURE DATA LAYER</p><h2>Persistence and spatial readiness</h2></div><Database size={19} /></div><div className='persistence-grid'><div><span>Backend</span><strong>{data.persistence.backend}</strong></div><div><span>Geometry storage</span><strong>{data.persistence.spatial.geometry_storage.replaceAll('_', ' ')}</strong></div><div><span>PostGIS</span><strong>{data.persistence.spatial.postgis ? data.persistence.spatial.version ?? 'Available' : 'Not enabled locally'}</strong></div><div><span>ML model</span><strong>{data.ml.version} · {data.ml.data_mode}</strong></div>{Object.entries(data.persistence.entity_counts).map(([name, count]) => <div key={name}><span>{name.replaceAll('_', ' ')}</span><strong>{count}</strong></div>)}</div></article>
      <article className='admin-card audit-card'><div className='analytics-head'><div><p className='eyebrow'>ACCOUNTABILITY</p><h2>Recent audit history</h2></div><Activity size={19} /></div><div className='audit-list'>{data.audit_events.map((event) => <div key={event.id}><span>{new Date(event.created_at).toLocaleString('en-IN')}</span><strong>{event.event_type.replaceAll('_', ' ')}</strong><small>{event.actor} · {event.changed_entities.length} changed entities</small></div>)}</div></article>
    </div>
  </section>
}
