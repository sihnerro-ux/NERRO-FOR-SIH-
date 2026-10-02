import type { FieldIncidentReportRequest } from '../types/api'

const DATABASE_NAME = 'ner-logistics-offline'
const DATABASE_VERSION = 1
const STORE_NAME = 'field-reports'
const LEGACY_STORAGE_KEY = 'ner-logistics-offline-field-reports'

export interface QueuedFieldReport {
  id: string
  queuedAt: string
  report: FieldIncidentReportRequest
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = window.indexedDB.open(DATABASE_NAME, DATABASE_VERSION)
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE_NAME)) {
        request.result.createObjectStore(STORE_NAME, { keyPath: 'id' })
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error ?? new Error('Offline report database could not be opened.'))
  })
}

function completeTransaction(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve()
    transaction.onerror = () => reject(transaction.error ?? new Error('Offline report transaction failed.'))
    transaction.onabort = () => reject(transaction.error ?? new Error('Offline report transaction was aborted.'))
  })
}

export async function loadQueuedReports(): Promise<QueuedFieldReport[]> {
  const database = await openDatabase()
  const transaction = database.transaction(STORE_NAME, 'readonly')
  const request = transaction.objectStore(STORE_NAME).getAll()
  const reports = await new Promise<QueuedFieldReport[]>((resolve, reject) => {
    request.onsuccess = () => resolve(request.result as QueuedFieldReport[])
    request.onerror = () => reject(request.error ?? new Error('Offline reports could not be read.'))
  })
  await completeTransaction(transaction)
  database.close()

  const legacyValue = window.localStorage.getItem(LEGACY_STORAGE_KEY)
  if (!legacyValue) return reports.sort((a, b) => a.queuedAt.localeCompare(b.queuedAt))
  try {
    const legacyReports = JSON.parse(legacyValue) as QueuedFieldReport[]
    const combined = [...reports]
    for (const legacy of legacyReports) {
      if (!combined.some((item) => item.id === legacy.id)) combined.push(legacy)
    }
    await saveQueuedReports(combined)
    window.localStorage.removeItem(LEGACY_STORAGE_KEY)
    return combined.sort((a, b) => a.queuedAt.localeCompare(b.queuedAt))
  } catch {
    return reports.sort((a, b) => a.queuedAt.localeCompare(b.queuedAt))
  }
}

export async function saveQueuedReports(reports: QueuedFieldReport[]): Promise<void> {
  const database = await openDatabase()
  const transaction = database.transaction(STORE_NAME, 'readwrite')
  const store = transaction.objectStore(STORE_NAME)
  store.clear()
  reports.forEach((report) => store.put(report))
  await completeTransaction(transaction)
  database.close()
}

export function queueReport(report: FieldIncidentReportRequest): QueuedFieldReport {
  const id = `OFFLINE-${crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`}`
  return { id, queuedAt: new Date().toISOString(), report: { ...report, client_report_id: id } }
}
