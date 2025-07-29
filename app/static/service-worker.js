const CACHE_NAME = 'origin-pwa';
const OFFLINE_URL = '/static/offline.html';
const urlsToCache = ['/', '/static/app.js', '/static/api.js', OFFLINE_URL];
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(urlsToCache))
  );
});
self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((res) => (res.ok ? res : caches.match(OFFLINE_URL)))
        .catch(() => caches.match(OFFLINE_URL))
    );
  } else {
    event.respondWith(
      caches.match(event.request).then((response) => response || fetch(event.request))
    );
  }
});
