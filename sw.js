const CACHE_NAME = 'navipark-pro-v1';
const ASSETS_TO_CACHE = [
  './',
  'https://cdn-icons-png.flaticon.com/512/1048/1048314.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Network-first strategy for dynamic mapping/API requests, cache fallback for assets
  if (event.request.url.includes('api.openchargemap.io') || event.request.url.includes('router.project-osrm.org')) {
    return fetch(event.request);
  }
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
