// Kosong saja sudah cukup untuk memenuhi syarat PWA
self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('fetch', (e) => {
  // Tidak perlu caching offline karena data dinamis dari server
});
