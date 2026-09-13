const CACHE_NAME = 'navipark-jaipur-v1';
const ASSETS_TO_CACHE = [
  './',
  'https://cdn-icons-png.flaticon.com/512/1048/1048314.png'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch(() => {
        // Safe fallback if CDN icon blocks offline cache preloading
      });
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            return caches.delete(name);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Bypass non-GET requests and Streamlit dynamic core/websocket/stream traffic
  if (
    event.request.method !== 'GET' ||
    url.pathname.includes('_stcore') ||
    url.pathname.includes('stream') ||
    url.protocol === 'chrome-extension:'
  ) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        // Cache same-origin assets or icons dynamically
        if (url.origin === self.location.origin || url.hostname.includes('flaticon.com')) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return networkResponse;
      })
      .catch(() => {
        return caches.match(event.request).then((cachedResponse) => {
          return cachedResponse || caches.match('./');
        });
      })
  );
});

