/*
 * Healvio backend connector
 * ------------------------------------------------------------
 * Connects the app (index.html) to:
 *   - Firebase Authentication   → phone OTP + Google sign-in ("auth")
 *   - Firebase Cloud Firestore  → shared database             ("db")
 *   - Your AI server (Claude)   → AI features                  ("sample")
 *   - Firebase Cloud Messaging  → phone notifications          ("push")
 *
 * The app asks for these through window.healvioBackend.use(name).
 * If something isn't configured in config.js, it returns null and
 * the app falls back to the offline demo for that feature.
 *
 * You normally don't need to edit this file.
 */
(function () {
  'use strict';
  var FIREBASE_SDK_VERSION = '13.2.0'; // https://firebase.google.com/support/releases
  var C = window.HEALVIO_CONFIG || {};
  // One worker link ("server" in config.js) powers AI, phone notifications and call relays
  if (C.server) {
    var S = String(C.server).trim().replace(/\/+$/, '');
    if (!C.aiUrl && C.ai === true) C.aiUrl = S;
    if (!C.turnUrl) C.turnUrl = S + '/ice';
    if (!C.pushUrl && C.vapidKey) C.pushUrl = S + '/push';
    // AI and PayPal switch on by themselves once the worker has them (no config change needed)
    var aiAuto = !C.aiUrl && C.ai !== false;
    var applyStatus = function (j) {
      var before = [!!C.aiUrl, C.listenUrl || '', C.payUrl || '', JSON.stringify(C.status || null)].join('|');
      C.status = j || {};
      C.readRxUrl = j && j.readRx ? S + '/read-rx' : '';
      if (aiAuto) {
        C.aiUrl = j && j.ai ? S : (C.ai === true ? S : '');
        C.listenUrl = j && j.listen ? S + '/listen' : '';
      }
      var pp = j && j.paypal;
      if (C.paypal !== false) {
        C.paypal = pp && pp.clientId ? { clientId: String(pp.clientId), sandbox: pp.env !== 'live', currency: String(pp.currency || 'USD'), rate: +pp.rate > 0 ? +pp.rate : 95 } : null;
        C.payUrl = C.paypal ? S + '/pay' : '';
      }
      if (before !== [!!C.aiUrl, C.listenUrl || '', C.payUrl || '', JSON.stringify(C.status || null)].join('|')) { try { window.dispatchEvent(new Event('healvio-ai')); } catch (e) {} }
    };
    try { var saved = JSON.parse(localStorage.getItem('healvio:aiStatus') || 'null'); if (saved) applyStatus(saved); } catch (e) {}
    fetch(S + '/status', { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (!j) return;
      try { localStorage.setItem('healvio:aiStatus', JSON.stringify(j)); } catch (e) {}
      applyStatus(j);
    }).catch(function () {});
  }
  var cache = {};
  var backend = { error: '' };

  /* ---------------- Firestore ---------------- */
  var SDK = 'https://www.gstatic.com/firebasejs/' + FIREBASE_SDK_VERSION + '/';
  var fsPromise = null;
  function loadFirestore() {
    if (!C.firebase || !C.firebase.projectId) return Promise.resolve(null);
    if (!fsPromise) {
      fsPromise = Promise.all([import(SDK + 'firebase-app.js'), import(SDK + 'firebase-firestore.js')])
        .then(function (mods) {
          var appMod = mods[0], fs = mods[1];
          var app = appMod.initializeApp(C.firebase), db = null;
          // keep a copy of the data on the phone: opening Healvio again reads only what changed
          // (this keeps Healvio inside Firebase's free 50,000 reads a day)
          if (fs.initializeFirestore && fs.persistentLocalCache) {
            try {
              db = fs.initializeFirestore(app, { localCache: fs.persistentLocalCache(fs.persistentMultipleTabManager ? { tabManager: fs.persistentMultipleTabManager() } : {}) });
              backend.cacheOn = true;
            } catch (e) { db = null; backend.cacheOn = false; }
          }
          if (!db) db = fs.getFirestore(app);
          return { fs: fs, db: db, app: app };
        });
    }
    return fsPromise;
  }

  /* ---------------- Authentication (phone OTP + Google) ---------------- */
  var authPromise = null;
  function loadAuth() {
    if (!C.firebase || !C.firebase.projectId) return Promise.resolve(null);
    if (!authPromise) {
      authPromise = loadFirestore().then(function (F) {
        return import(SDK + 'firebase-auth.js').then(function (A) { return { A: A, auth: A.getAuth(F.app) }; });
      });
    }
    return authPromise;
  }
  var AUTH_MSG = {
    'auth/invalid-phone-number': 'That phone number looks wrong. Please check it.',
    'auth/missing-phone-number': 'Please enter your phone number.',
    'auth/too-many-requests': 'Too many attempts. Please wait a while and try again.',
    'auth/quota-exceeded': 'The SMS limit was reached. Please try again later.',
    'auth/invalid-verification-code': "That code didn't match. Check the SMS and try again.",
    'auth/code-expired': 'That code expired. Tap "Change number / resend" for a new one.',
    'auth/billing-not-enabled': 'SMS login needs the Firebase Blaze plan (README step 2).',
    'auth/operation-not-allowed': 'This sign-in method is off. Turn it on in Firebase → Authentication → Sign-in method.',
    'auth/unauthorized-domain': 'This website is not listed in Firebase → Authentication → Settings → Authorized domains.',
    'auth/captcha-check-failed': 'The security check failed. Reload the page and try again.',
    'auth/network-request-failed': 'No internet connection. Please try again.',
    'auth/requires-recent-login': 'For your safety, log out, log in again, then delete your account.',
    'auth/popup-blocked': 'Your browser blocked the Google window. Allow pop-ups and try again.',
    'auth/user-disabled': 'This account has been disabled.'
  };
  function authErr(e) {
    var c = (e && e.code) || '';
    if (c === 'auth/popup-closed-by-user' || c === 'auth/cancelled-popup-request') return { code: 'cancelled' };
    return { code: c || 'error', userMessage: AUTH_MSG[c] || ('Sign-in problem: ' + (c || (e && e.message) || 'unknown error')) };
  }
  function freshCaptchaBox() {
    var old = document.getElementById('recaptcha-box');
    var box = document.createElement('div'); box.id = 'recaptcha-box';
    if (old) old.replaceWith(box); else document.body.appendChild(box);
  }
  function makeAuth(X) {
    var A = X.A, auth = X.auth, verifier = null, confirmation = null;
    try { auth.useDeviceLanguage(); } catch (e) {}
    try { A.getRedirectResult(auth).catch(function () {}); } catch (e) {}
    function userOf(u) { return u ? { uid: u.uid, phone: u.phoneNumber || '', email: u.email || '', name: u.displayName || '' } : null; }
    function getVerifier() {
      if (!verifier) { if (!document.getElementById('recaptcha-box')) freshCaptchaBox(); verifier = new A.RecaptchaVerifier(auth, 'recaptcha-box', { size: 'invisible' }); }
      return verifier;
    }
    function resetVerifier() { try { if (verifier) verifier.clear(); } catch (e) {} verifier = null; freshCaptchaBox(); }
    return {
      onChange: function (cb) { return A.onAuthStateChanged(auth, function (u) { cb(userOf(u)); }); },
      sendOtp: function (phone) {
        var v;
        try { v = getVerifier(); } catch (e) { resetVerifier(); return Promise.reject(authErr(e)); }
        return A.signInWithPhoneNumber(auth, phone, v).then(function (c) { confirmation = c; }, function (e) { resetVerifier(); throw authErr(e); });
      },
      verifyOtp: function (code) {
        if (!confirmation) return Promise.reject({ userMessage: 'Please request a new code.' });
        return confirmation.confirm(code).then(function (r) { confirmation = null; return userOf(r.user); }, function (e) { throw authErr(e); });
      },
      google: function () {
        var p = new A.GoogleAuthProvider();
        return A.signInWithPopup(auth, p).then(function (r) { return userOf(r.user); }, function (e) {
          if (e && (e.code === 'auth/popup-blocked' || e.code === 'auth/operation-not-supported-in-this-environment')) return A.signInWithRedirect(auth, p);
          throw authErr(e);
        });
      },
      signOut: function () { return A.signOut(auth); },
      idToken: function () { return auth.currentUser ? auth.currentUser.getIdToken() : Promise.resolve(''); },
      deleteUser: function () { return auth.currentUser ? A.deleteUser(auth.currentUser).catch(function (e) { throw authErr(e); }) : Promise.resolve(); }
    };
  }

  // Firestore error codes → the codes the app understands
  function mapErr(e) {
    var code = (e && e.code) || '';
    var out = { code: 'unavailable', message: String((e && e.message) || e) };
    if (code === 'permission-denied' || code === 'invalid-argument' || code === 'failed-precondition') out.code = 'invalid_argument';
    else if (code === 'resource-exhausted') out.code = 'resource_exhausted';
    if (code === 'permission-denied') console.warn('[Healvio] Firestore refused this write/read. Check firebase/firestore.rules (they may have expired).');
    return out;
  }

  function wrapDoc(s) {
    return {
      id: s.id,
      exists: typeof s.exists === 'function' ? s.exists() : !!s.exists,
      data: function () { return s.data(); },
      metadata: { fromCache: !!(s.metadata && s.metadata.fromCache), hasPendingWrites: !!(s.metadata && s.metadata.hasPendingWrites) }
    };
  }
  function wrapQuery(s) {
    var docs = s.docs.map(wrapDoc);
    return {
      docs: docs, size: docs.length, empty: !docs.length,
      docChanges: function () { return []; },
      metadata: { fromCache: !!(s.metadata && s.metadata.fromCache), hasPendingWrites: !!(s.metadata && s.metadata.hasPendingWrites) }
    };
  }

  function makeDb(F) {
    var fs = F.fs, db = F.db;
    function docRef(path) {
      var ref = fs.doc(db, path);
      return {
        id: ref.id, path: path,
        get: function () { return fs.getDoc(ref).then(wrapDoc, function (e) { throw mapErr(e); }); },
        set: function (d) { return fs.setDoc(ref, d).catch(function (e) { throw mapErr(e); }); },
        update: function (d) { return fs.updateDoc(ref, d).catch(function (e) { throw mapErr(e); }); },
        delete: function () { return fs.deleteDoc(ref).catch(function (e) { throw mapErr(e); }); },
        onSnapshot: function (next, err) {
          return fs.onSnapshot(ref, function (s) { next(wrapDoc(s)); }, function (e) { if (err) err(mapErr(e)); });
        },
        collection: function (sub) { return colRef(path + '/' + sub, []); }
      };
    }
    function colRef(path, cons) {
      var base = fs.collection(db, path);
      function q() { return cons.length ? fs.query.apply(null, [base].concat(cons)) : base; }
      return {
        path: path,
        where: function (f, op, v) { return colRef(path, cons.concat([fs.where(f, op, v)])); },
        orderBy: function (f, dir) { return colRef(path, cons.concat([fs.orderBy(f, dir || 'asc')])); },
        limit: function (n) { return colRef(path, cons.concat([fs.limit(n)])); },
        get: function () { return fs.getDocs(q()).then(wrapQuery, function (e) { throw mapErr(e); }); },
        onSnapshot: function (next, err) {
          return fs.onSnapshot(q(), function (s) { next(wrapQuery(s)); }, function (e) { if (err) err(mapErr(e)); });
        },
        doc: function (id) { return docRef(path + '/' + (id || fs.doc(base).id)); },
        add: function (d) { var r = this.doc(); return r.set(d).then(function () { return r; }); }
      };
    }
    return { doc: docRef, collection: function (p) { return colRef(p, []); } };
  }

  /* ---------------- AI (your Cloudflare Worker → Claude) ---------------- */
  function parseJson(t) {
    try { return JSON.parse(t); } catch (e) {}
    var m = t.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (m) { try { return JSON.parse(m[1]); } catch (e) {} }
    var a = t.indexOf('{'), b = t.indexOf('[');
    var i = a < 0 ? b : b < 0 ? a : Math.min(a, b);
    var j = Math.max(t.lastIndexOf('}'), t.lastIndexOf(']'));
    if (i >= 0 && j > i) { try { return JSON.parse(t.slice(i, j + 1)); } catch (e) {} }
    throw { code: 'invalid_json', text: t, userMessage: "AI replied in an unexpected format. Please try again." };
  }
  // the signed-in person's Firebase token (the worker checks it)
  function idToken() {
    return loadAuth().then(function (X) { return X && X.auth.currentUser ? X.auth.currentUser.getIdToken() : ''; }).catch(function () { return ''; });
  }
  backend.idToken = idToken;

  function makeSample() {
    if (!C.aiUrl) return null;
    function call(input, opts) {
      opts = opts || {};
      var prompt = typeof input === 'string' ? input : (input || []).map(function (m) { return m.content; }).join('\n\n');
      return idToken().then(function (tok) {
        var h = { 'content-type': 'application/json' };
        if (tok) h.authorization = 'Bearer ' + tok;
        return fetch(C.aiUrl, { method: 'POST', headers: h, body: JSON.stringify({ prompt: prompt, tier: opts.modelTier || 'default' }), signal: opts.signal });
      }).then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (j) {
          if (res.status === 429 && j.error === 'free_limit') throw { code: 'rate_limited', userMessage: "Today's free AI limit is used up. It starts again at 5:30 AM." };
          if (res.status === 429) throw { code: 'rate_limited', userMessage: 'AI is busy right now. Please try again in a minute.' };
          if (res.status === 401) throw { code: 'not_granted', userMessage: 'Please sign in again to use AI.' };
          if (res.status === 403) throw { code: 'not_granted', userMessage: 'The AI server refused this website. Add this site to ALLOWED_ORIGINS on your worker.' };
          if (!res.ok) throw { code: 'upstream_error', userMessage: 'AI server error: ' + (j.error || res.status) };
          if (!j.text) throw { code: 'empty_completion', userMessage: 'AI returned an empty answer. Please try again.' };
          return { text: j.text, truncated: !!j.truncated };
        });
      }, function (e) {
        if (e && e.name === 'AbortError') throw { code: 'cancelled' };
        throw { code: 'upstream_error', userMessage: "Couldn't reach the AI server. Check aiUrl in config.js." };
      });
    }
    var sample = function (input, opts) { return call(input, opts); };
    sample.json = function (input, opts) {
      var p = typeof input === 'string' ? input + '\n\nReply with the JSON only, no other text.' : input;
      return call(p, opts).then(function (r) { return parseJson(r.text); });
    };
    sample.limits = function () { return Promise.resolve({ maxPromptBytes: 200000 }); };
    return sample;
  }

  /* ---------------- phone notifications (Firebase Cloud Messaging) ---------------- */
  // a real Web Push key: 65 bytes, starts with 4 and is a point on the P-256 curve
  function vapidOk(k) {
    try {
      var t = String(k || '').trim().replace(/-/g, '+').replace(/_/g, '/');
      while (t.length % 4) t += '=';
      var b = atob(t);
      if (b.length !== 65 || b.charCodeAt(0) !== 4 || !(window.crypto && crypto.subtle)) return Promise.resolve(b.length === 65 && b.charCodeAt(0) === 4);
      var u = new Uint8Array(65); for (var i = 0; i < 65; i++) u[i] = b.charCodeAt(i);
      return crypto.subtle.importKey('raw', u, { name: 'ECDH', namedCurve: 'P-256' }, false, []).then(function () { return true; }, function () { return false; });
    } catch (e) { return Promise.resolve(false); }
  }
  backend.vapidCheck = vapidOk;
  function makePush() {
    if (!C.vapidKey || !C.pushUrl || !('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) return Promise.resolve(null);
    return loadFirestore().then(function (F) {
      return import(SDK + 'firebase-messaging.js').then(function (M) {
        return Promise.resolve(M.isSupported ? M.isSupported() : true).then(function (ok) {
          if (!ok) { window.healvioBackend.pushError = new Error('unsupported'); return null; }
          var messaging = M.getMessaging(F.app);
          return {
            // this phone's notification address; uses Healvio's own service worker (sw.js)
            // fresh = Google said the old address is dead: throw it away and make a new one
            token: function (fresh) {
              return navigator.serviceWorker.ready.then(function (reg) {
                var key = String(C.vapidKey || '').trim();
                // a phone-side registration problem (worth clearing and retrying); Google project settings are not
                var isPushErr = function (e) { var t = String((e && e.code) || '') + ' ' + String((e && (e.message || e.name)) || e); return !/Registration API|Installations|API key|has not been used|is disabled|PERMISSION_DENIED|referer|blocked/i.test(t) && /push service|Registration failed|AbortError|applicationServerKey|subscription|token-subscribe|token-unsubscribe/i.test(t); };
                // useKey false = Firebase's own public key (always valid), used when the key in config.js is wrong
                var get = function (useKey) { var o = { serviceWorkerRegistration: reg }; if (useKey) o.vapidKey = key; return M.getToken(messaging, o); };
                // an old registration left on this phone (often after a key change): clear it before trying again
                var clear = function () {
                  return Promise.resolve(reg.pushManager && reg.pushManager.getSubscription()).then(function (sub) { return sub ? sub.unsubscribe() : null; }).catch(function () {})
                    .then(function () { return M.deleteToken ? M.deleteToken(messaging).catch(function () {}) : null; })
                    .then(function () { return new Promise(function (r) { setTimeout(r, 1200); }); });
                };
                return vapidOk(key).then(function (good) {
                  backend.vapidOk = good;
                  var first = function () { return good ? get(true) : Promise.reject(new Error('Registration failed - the vapidKey in config.js is not a valid key')); };
                  return (fresh ? clear().then(first) : first())
                    .catch(function (e) {
                      if (good && !isPushErr(e)) throw e;
                      return clear().then(function () { return get(good); })
                        .catch(function (e2) { if (!isPushErr(e2)) throw e2; return clear().then(function () { return get(false); }); });
                    });
                });
              });
            }
          };
        });
      });
    }).catch(function (e) { window.healvioBackend.pushError = e; console.warn('[Healvio] phone notifications are not available here:', e); return null; });
  }

  /* ---------------- public entry point ---------------- */
  backend.use = function (name) {
    if (name in cache && !(name === 'sample' && !cache[name])) return Promise.resolve(cache[name]);
    var p;
    if (name === 'auth') {
      p = loadAuth().then(function (X) { return X ? makeAuth(X) : null; }, function (e) {
        backend.error = String((e && e.message) || e).slice(0, 140);
        console.error('[Healvio] Firebase sign-in failed to start:', e);
        return null;
      });
    } else if (name === 'db') {
      p = loadFirestore().then(function (F) { return F ? makeDb(F) : null; }, function (e) {
        backend.error = String((e && e.message) || e).slice(0, 140);
        console.error('[Healvio] Firebase failed to start:', e);
        return null;
      });
    } else if (name === 'sample') {
      p = Promise.resolve(makeSample());
    } else if (name === 'push') {
      p = makePush();
    } else {
      p = Promise.resolve(null); // e.g. "downloads": the app uses a normal browser download instead
    }
    return p.then(function (v) { cache[name] = v; return v; });
  };

  // on log out: remove the copy of the data kept on this phone (private health records)
  backend.clearLocal = function () {
    return loadFirestore().then(function (F) {
      if (!F || !backend.cacheOn || !F.fs.terminate || !F.fs.clearIndexedDbPersistence) return false;
      return F.fs.terminate(F.db).then(function () { return F.fs.clearIndexedDbPersistence(F.db); }).then(function () { return true; });
    }).catch(function () { return false; });
  };
  window.healvioBackend = backend;
})();
