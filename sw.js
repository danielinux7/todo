// Bump CACHE on every deploy that changes a shell file, or clients serve stale copies.
// ponytail: manual version string — no build step. Add a content-hash bumper if deploys get frequent.
const CACHE = 'todo-v9';
const SHELL = ['.', 'index.html', 'manifest.webmanifest', 'icon.svg'];

self.addEventListener('install', e =>
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL))));

self.addEventListener('activate', e =>
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim())));

// Page asks the waiting worker to take over (the "New version" button).
self.addEventListener('message', e => { if (e.data === 'skip') self.skipWaiting(); });

// Stale-while-revalidate: serve cache instantly, refresh it in the background.
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET' || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(caches.open(CACHE).then(async c => {
    const cached = await c.match(e.request);
    const net = fetch(e.request)
      .then(r => { if (r.ok) c.put(e.request, r.clone()); return r; })
      .catch(() => cached);
    return cached || net;
  }));
});
