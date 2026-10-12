{% comment %} Confoinfo 서비스 워커 (010). views.service_worker 가 그린다 — 경로와 판 번호를 박아 넣는다.

네트워크 먼저, 안 되면 캐시. 학회장 와이파이가 느리면 4초를 기다린 뒤 캐시에 있는 것을 낸다
(그래도 받던 것은 받아서 캐시를 고친다). 받은 것은 전부 캐시에 남긴다 — 한 번 본 화면은
끊긴 곳에서도 열린다. 다른 출처(번역·Scholar 링크)는 건드리지 않는다. {% endcomment %}
var CACHE = "{{ cache }}";
var SHELL = {{ shell|safe }};
var OFFLINE = "{{ offline }}";
var WAIT_MS = 4000;

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(SHELL); })
    .then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k.indexOf("confoinfo-") === 0 && k !== CACHE; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  var net = fetch(req).then(function (res) {
    if (res.ok) {
      var copy = res.clone();
      caches.open(CACHE).then(function (c) { c.put(req, copy); });
    }
    return res;
  });
  e.waitUntil(net.catch(function () {}));
  e.respondWith(new Promise(function (resolve) {
    var done = false;
    function fromCache() {
      return caches.match(req, { ignoreSearch: true }).then(function (hit) {
        return hit || (req.mode === "navigate" ? caches.match(OFFLINE) : undefined);
      });
    }
    var timer = setTimeout(function () {
      fromCache().then(function (hit) { if (hit && !done) { done = true; resolve(hit); } });
    }, WAIT_MS);
    net.then(function (res) { if (!done) { done = true; clearTimeout(timer); resolve(res); } })
      .catch(function () {
        clearTimeout(timer);
        fromCache().then(function (hit) {
          if (!done) { done = true; resolve(hit || Response.error()); }
        });
      });
  }));
});
