const SHELL_CACHE = 'ner-logistics-shell-v2'
const SHELL_FILES = ['/manifest.webmanifest', '/icons/ner-logistics.svg', '/icons/ner-logistics-maskable.svg', '/icons/nerro.PNG', '/icons/national%20emblem.png', '/icons/flag.png']

async function cacheApplicationShell() {
  const cache = await caches.open(SHELL_CACHE)
  await cache.addAll(SHELL_FILES)
  const indexResponse = await fetch('/')
  const indexHtml = await indexResponse.clone().text()
  await cache.put('/', indexResponse)
  const buildAssets = [...indexHtml.matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g)].map((match) => match[1])
  if (buildAssets.length) await cache.addAll(buildAssets)
}

self.addEventListener('install', (event) => {
  event.waitUntil(cacheApplicationShell().then(() => self.skipWaiting()))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== SHELL_CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  const url = new URL(request.url)
  if (request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/') || url.pathname === '/health') return

  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).then((response) => {
      const copy = response.clone()
      void caches.open(SHELL_CACHE).then((cache) => cache.put('/', copy))
      return response
    }).catch(() => caches.match('/')))
    return
  }

  event.respondWith(caches.match(request).then((cached) => cached ?? fetch(request).then((response) => {
    if (response.ok) {
      const copy = response.clone()
      void caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy))
    }
    return response
  })))
})
