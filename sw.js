/* Healvio service worker: lets the app install on phones and open without internet.
 * Always tries the network first so updates appear right away. */
const CACHE = 'healvio-v10';
const LANG = 'healvio-lang'; // the patient's app language, saved by Healvio for phone pop-ups
const SHELL = ['./', './index.html', './config.js', './backend.js', './privacy.html', './terms.html', './manifest.webmanifest', './icons/icon-192.png', './icons/icon-512.png', './icons/badge-96.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => {
    const old = keys.filter(k => k !== CACHE && k !== LANG);
    // phones still running a version without auto-update (v1–v4) are moved to the new one right away
    const veryOld = old.some(k => /^healvio-v[1-4]$/.test(k));
    return Promise.all(old.map(k => caches.delete(k)))
      .then(() => self.clients.claim())
      .then(() => self.clients.matchAll({ type: 'window' }))
      .then(list => list.forEach(c => {
        if (veryOld && c.navigate) c.navigate(c.url).catch(() => {});
        else c.postMessage({ type: 'updated' });
      }));
  }));
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== self.location.origin) return; // Firebase & AI calls go straight to the network
  if (url.pathname.endsWith('/version.json')) return; // update check always asks the server
  // newest version from the internet; if the network is slow (over 2.5 s), open instantly from the phone
  const fromCache = () => caches.match(e.request).then(r => r || (e.request.mode === 'navigate' ? caches.match('./index.html') : undefined));
  e.respondWith(new Promise(resolve => {
    let done = false;
    const finish = r => { if (!done && r) { done = true; resolve(r); } };
    const slow = setTimeout(() => fromCache().then(finish), 2500);
    fetch(e.request)
      .then(res => { if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); } clearTimeout(slow); finish(res); })
      .catch(() => { clearTimeout(slow); fromCache().then(r => { if (r) finish(r); else if (!done) { done = true; resolve(Response.error()); } }); });
  }));
});

// Pop-ups in the patient's language: the same sentence patterns as the Alerts list in the app.
// Names, prices, times and words people typed stay as they were written.
function langPack() {
  try { return caches.open(LANG).then(c => c.match(self.registration.scope + '__lang')).then(r => r ? r.json() : null).catch(() => null); }
  catch (e) { return Promise.resolve(null); } // no saved language: the pop-up shows as sent
}
const MD = /\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b/g;
function turnNote(s, P) {
  if (!P._rx) P._rx = (P.tpl || []).map(([src, types, tr, lit]) => { try { return { rx: new RegExp(src), types, tr, lit: lit || 0 }; } catch (e) { return null; } }).filter(Boolean);
  let rest = String(s || '').replace(/\s+/g, ' ').trim(), out = '', hit = 0;
  while (rest) {
    let best = null;
    for (const p of P._rx) {
      const m = p.rx.exec(rest);
      if (m && (!best || m[0].length > best.m[0].length || (m[0].length === best.m[0].length && p.lit > best.p.lit))) best = { m, p };
    }
    if (!best) break;
    const vals = best.m.slice(1).map((v, i) => {
      const t = best.p.types[i];
      if (t === 'date') return (P.words || {})[v] || v.replace(MD, x => (P.loc || {})[x] || x);
      if (t === 'dr' || t === 'name' || t === 'store' || t === 'rider') return (P.names || {})[v.trim()] || v; // names as the app shows them
      return v;
    });
    out += (out ? ' ' : '') + best.p.tr.replace(/\{(\d+)\}/g, (x, i) => vals[+i] !== undefined ? vals[+i] : x);
    rest = rest.slice(best.m[0].length).trim(); hit++;
  }
  return hit ? (rest ? out + ' ' + rest : out) : null;
}
function turnTitle(t, P) {
  const m = /^((?:🔔 )?Healvio · |[^\sA-Za-z0-9]+ )?(.*)$/.exec(String(t || '')), w = (P.words || {})[m[2]];
  return w ? (m[1] || '') + w : t;
}
function inLang(d) {
  return langPack().then(P => {
    if (!P || !P.on) return d;
    try {
      let body = d.body || '';
      const i = body.indexOf(': ');
      const chat = d.kind === 'alert' && /[?&]go=room/.test(d.url || '') && !/^(▶️|Missed (video|voice) call from )/.test(body) && i > 0 && i < 80; // chat messages ("Name: message") stay as typed
      if (chat) { const nm = (P.names || {})[body.slice(0, i).trim()]; if (nm) body = nm + body.slice(i); } // the sender's name turned, the message as typed
      else body = turnNote(body, P) || body;
      return Object.assign({}, d, { title: turnTitle(d.title || 'Healvio', P), body, answer: (P.words || {}).Answer });
    } catch (e) { return d; }
  });
}

// Phone notifications sent by your worker (Firebase Cloud Messaging)
self.addEventListener('push', e => {
  let p = {};
  try { p = e.data ? e.data.json() : {}; } catch (er) { p = { data: { body: e.data ? e.data.text() : '' } }; }
  const d0 = Object.assign({}, p.notification || {}, p.data || {});
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    // Healvio is on screen: it already shows the alert or rings for the call itself
    if (list.some(c => c.visibilityState === 'visible')) return;
    return inLang(d0).then(d => {
      const call = d.kind === 'call', ended = d.kind === 'callend', urgent = d.kind === 'urgent';
      const opts = {
        body: d.body || '', icon: 'icons/icon-192.png', badge: 'icons/badge-96.png',
        data: { url: d.url || './' }, tag: d.tag || undefined, timestamp: Date.now(), silent: false,
        // calls ring again with every push and stay until answered; a missed call quietly replaces the ringing
        renotify: !!d.tag && !ended, requireInteraction: call || urgent,
        vibrate: call ? [800, 400, 800, 400, 800, 400, 800] : urgent ? [400, 150, 400, 150, 400] : [250, 120, 250],
        actions: call ? [{ action: 'answer', title: '✅ ' + (d.answer || 'Answer') }] : []
      };
      return self.registration.showNotification(d.title || 'Healvio', opts);
    });
  }));
});

// Tapping a notification opens Healvio on the right screen
self.addEventListener('notificationclick', e => {
  e.notification.close();
  let url = new URL((e.notification.data && e.notification.data.url) || './', self.registration.scope).href;
  if (e.action === 'answer') url += (url.includes('?') ? '&' : '?') + 'answer=1';
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    for (const c of list) { if ('focus' in c) { c.postMessage({ type: 'nav', url }); return c.focus(); } }
    return self.clients.openWindow ? self.clients.openWindow(url) : null;
  }));
});
