// Service Worker : réseau d'abord (contenu toujours à jour), cache en secours hors ligne.
const V = 'futura-v3';
const SHELL = ['/', '/static/app.js', '/static/style.css', '/static/icon.svg', '/manifest.webmanifest'];

self.addEventListener('install', e => e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener('activate', e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim())));

self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api/parent')) return;
  e.respondWith(fetch(req).then(r => { if (r.ok) { const c = r.clone(); caches.open(V).then(x => x.put(req, c)); } return r; })
    .catch(() => caches.match(req)));
});
