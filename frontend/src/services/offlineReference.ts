const DATABASE_NAME = 'ner-logistics-reference'
const DATABASE_VERSION = 1
const STORE_NAME = 'operational-snapshots'

interface CachedRecord<T> {
  key: string
  payload: T
  updatedAt: string
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = window.indexedDB.open(DATABASE_NAME, DATABASE_VERSION)
    request.onupgradeneeded = () => {
      const database = request.result
      if (!database.objectStoreNames.contains(STORE_NAME)) database.createObjectStore(STORE_NAME, { keyPath: 'key' })
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function saveOperationalSnapshot<T>(key: string, payload: T): Promise<void> {
  if (!('indexedDB' in window)) return
  const database = await openDatabase()
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, 'readwrite')
    transaction.objectStore(STORE_NAME).put({ key, payload, updatedAt: new Date().toISOString() } satisfies CachedRecord<T>)
    transaction.oncomplete = () => resolve()
    transaction.onerror = () => reject(transaction.error)
  })
  database.close()
}

export async function loadOperationalSnapshot<T>(key: string): Promise<T | null> {
  if (!('indexedDB' in window)) return null
  const database = await openDatabase()
  const record = await new Promise<CachedRecord<T> | undefined>((resolve, reject) => {
    const request = database.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME).get(key)
    request.onsuccess = () => resolve(request.result as CachedRecord<T> | undefined)
    request.onerror = () => reject(request.error)
  })
  database.close()
  return record?.payload ?? null
}

export async function clearOperationalSnapshots(userId: string): Promise<void> {
  if (!('indexedDB' in window)) return
  const database = await openDatabase()
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, 'readwrite')
    const store = transaction.objectStore(STORE_NAME)
    const cursorRequest = store.openCursor()
    cursorRequest.onsuccess = () => {
      const cursor = cursorRequest.result
      if (!cursor) return
      if (String(cursor.key).startsWith(`${userId}:`)) cursor.delete()
      cursor.continue()
    }
    transaction.oncomplete = () => resolve()
    transaction.onerror = () => reject(transaction.error)
  })
  database.close()
}
