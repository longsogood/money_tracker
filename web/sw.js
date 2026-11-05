const CACHE = "money-tracker-v1";
const ASSETS = ["/", "/css/style.css", "/js/app.js", "/manifest.json", "/icon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api")) return; // API luôn lên mạng
  e.respondWith(
    caches.match(e.request).then(hit => hit || fetch(e.request))
  );
});
