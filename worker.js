/*
 * Healvio AI server — Cloudflare Worker
 * ------------------------------------------------------------
 * Keeps your Anthropic (Claude) API key secret and forwards the app's
 * AI requests (summary, translate, doubt check) to the Claude API.
 *
 * Settings (Cloudflare dashboard → your worker → Settings → Variables and Secrets):
 *   ANTHROPIC_API_KEY  (Secret)  your key from console.anthropic.com
 *   ALLOWED_ORIGINS    (Text)    comma-separated sites allowed to use it, e.g.
 *                                https://healvio.netlify.app,http://localhost:8080
 *   MODEL              (optional) default "claude-sonnet-5-5"
 *   QUICK_MODEL        (optional) default "claude-haiku-5-5"  (used for translation)
 *
 * FREE AI (Cloudflare Workers AI — no Claude key needed):
 *   Worker → Settings → Bindings → Add → Workers AI → Variable name: AI
 *   Then AI summary, doubt check, translate and call notes (speech-to-text) all work.
 *   Free: 10,000 "neurons" a day (resets 5:30 AM India time). Your data is not used to train AI.
 *   AI_MODEL / AI_QUICK_MODEL (optional Text) choose other Workers AI models.
 *   If ANTHROPIC_API_KEY is also set, text AI uses Claude instead; call notes still use Workers AI.
 *
 * Phone notifications (free):
 *   FIREBASE_SERVICE_ACCOUNT (Secret)  the whole JSON file from Firebase → Project settings →
 *                                      Service accounts → Generate new private key
 *   The app asks  https://<this worker>/push  to deliver each alert and incoming call.
 *
 * Video-call relay (optional, free up to 1,000 GB a month — see README "Video calls"):
 *   TURN_KEY_ID        (Text)    Cloudflare → Realtime → TURN → your key's "Turn Token ID"
 *   TURN_KEY_API_TOKEN (Secret)  that key's "API token"
 *   OR, free without a card (ExpressTURN, 1 TB a month — expressturn.com → Sign up → Dashboard):
 *   TURN_USERNAME (Text)    the dashboard's username
 *   TURN_PASSWORD (Secret)  the dashboard's password
 *   TURN_SERVER   (Text, optional)  the server shown, e.g. relay1.expressturn.com:3478
 *   The app gets call servers from  https://<this worker>/ice
 *
 * PayPal payments (free test mode — see README "PayPal"):
 *   PAYPAL_CLIENT_ID     (Text)    developer.paypal.com → Apps & Credentials → your app → Client ID
 *   PAYPAL_CLIENT_SECRET (Secret)  the same app's Secret key
 *   PAYPAL_ENV           (optional Text) "sandbox" (test money, default) or "live" (real money)
 *   PAY_CURRENCY         (optional Text) currency PayPal charges in, default "USD"
 *   INR_RATE             (optional Text) rupees per 1 unit of PAY_CURRENCY, default 95
 *   Patients pay the doctor's fee and medicine orders. The price is always read from the
 *   database here, never taken from the phone, and only this worker can mark something paid.
 *
 * Medicine reminders: Settings → Trigger events → Add → Cron triggers → Minute(s) = 1 (every minute).
 *   The worker then sends "Time for your medicines" alerts at the times each patient chose.
 *   The same trigger reminds doctors when a consultation's time is up (and 10 minutes later),
 *   and tells the next patients once that the doctor is about 10 minutes late.
 * Paper prescriptions: POST /read-rx reads a prescription photo with Workers AI (free).
 * Refunds: POST /pay/refund gives the money back through PayPal when an order or visit is cancelled.
 *
 * API reference: https://docs.claude.com/en/api/messages
 */
const API_URL = 'https://api.anthropic.com/v1/messages';

export default {
  // runs every minute (Cron trigger): medicine reminders, consultation time reminders, payment reminders
  async scheduled(event, env, ctx) { ctx.waitUntil(runReminders(env).catch(() => {})); },
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const allowed = String(env.ALLOWED_ORIGINS || '').split(',').map(s => s.trim()).filter(Boolean);
    const originOk = allowed.includes('*') || allowed.includes(origin);
    const cors = {
      'Access-Control-Allow-Origin': originOk ? (origin || '*') : 'null',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'content-type, authorization',
      'Access-Control-Max-Age': '86400',
      'Vary': 'Origin'
    };
    const reply = (obj, status = 200) =>
      new Response(JSON.stringify(obj), { status, headers: { ...cors, 'content-type': 'application/json' } });

    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });

    // ---- phone notifications: POST /push ----
    if (new URL(request.url).pathname.replace(/\/+$/, '') === '/push') {
      if (!originOk) return reply({ error: 'This website is not in ALLOWED_ORIGINS' }, 403);
      try { return await handlePush(request, env, reply); }
      catch (e) { return reply({ error: 'push failed', detail: String((e && e.message) || e).slice(0, 200) }, 502); }
    }

    const path = new URL(request.url).pathname.replace(/\/+$/, '');

    // ---- what this server can do: GET /status ----
    if (path === '/status') {
      if (!originOk) return reply({ error: 'This website is not in ALLOWED_ORIGINS' }, 403);
      return reply({ ai: !!(env.ANTHROPIC_API_KEY || env.AI), listen: !!(env.AI && env.FIREBASE_SERVICE_ACCOUNT), push: !!env.FIREBASE_SERVICE_ACCOUNT, turn: !!(env.TURN_KEY_ID && env.TURN_KEY_API_TOKEN) || fixedTurn(env).length > 0,
        paypal: payOn(env) ? { clientId: String(env.PAYPAL_CLIENT_ID).trim(), env: payLive(env) ? 'live' : 'sandbox', currency: payCur(env), rate: payRate(env) } : false,
        refund: payOn(env), readRx: !!env.AI, reminders: !!env.FIREBASE_SERVICE_ACCOUNT, summary: !!(env.AI && env.FIREBASE_SERVICE_ACCOUNT),
        ...(new URL(request.url).searchParams.get('check') === '1' ? { check: await healthCheck(request, env) } : {}) });
    }

    // ---- PayPal refund: POST /pay/refund {kind:'fee'|'order', id, reason} ----
    if (path === '/pay/refund') {
      if (!originOk) return reply({ error: 'This website is not in ALLOWED_ORIGINS' }, 403);
      if (request.method !== 'POST') return reply({ error: 'Use POST' }, 405);
      if (!payOn(env)) return reply({ error: 'PayPal is not set up on the worker' }, 500);
      try { return await handleRefund(request, env, reply); }
      catch (e) { return reply({ error: 'Refund failed. Please try again.', detail: String((e && e.message) || e).slice(0, 300) }, 502); }
    }
    // ---- read a paper prescription photo: POST /read-rx {image: dataURL} ----
    if (path === '/read-rx') {
      if (!originOk) return reply({ error: 'This website is not in ALLOWED_ORIGINS' }, 403);
      if (request.method !== 'POST') return reply({ error: 'Use POST' }, 405);
      if (!env.AI) return reply({ error: 'AI is not set up on the worker (add the Workers AI binding named AI)' }, 500);
      try { return await handleReadRx(request, env, reply); }
      catch (e) { return reply({ error: "AI couldn't read this photo. Please type the medicine names.", detail: String((e && e.message) || e).slice(0, 300) }, 502); }
    }

    // ---- PayPal: POST /pay/create {kind:'fee'|'order', id}  ·  POST /pay/capture {kind, id, orderID} ----
    if (path === '/pay/create' || path === '/pay/capture') {
      if (!originOk) return reply({ error: 'This website is not in ALLOWED_ORIGINS' }, 403);
      if (request.method !== 'POST') return reply({ error: 'Use POST' }, 405);
      if (!payOn(env)) return reply({ error: 'PayPal is not set up on the worker (add PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)' }, 500);
      try { return await handlePay(path.slice(5), request, env, reply); }
      catch (e) { return reply({ error: 'Payment failed. Please try again.', detail: String((e && e.message) || e).slice(0, 300) }, 502); }
    }

    // ---- AI consultation summary: POST /summary { rid, lang } (reads the whole chat, call notes and prescription) ----
    if (path === '/summary') {
      if (!originOk) return reply({ error: 'This website is not in ALLOWED_ORIGINS' }, 403);
      if (request.method !== 'POST') return reply({ error: 'Use POST' }, 405);
      if (!env.AI || !env.FIREBASE_SERVICE_ACCOUNT) return reply({ error: 'Add the Workers AI binding named AI and FIREBASE_SERVICE_ACCOUNT to this worker' }, 500);
      try { return await handleSummary(request, env, reply); }
      catch (e) { return aiFail(e, reply); }
    }

    // ---- AI call notes: POST /listen  { rid, audio: base64 WAV of one person's own voice } ----
    if (path === '/listen') {
      if (!originOk) return reply({ error: 'This website is not in ALLOWED_ORIGINS' }, 403);
      if (request.method !== 'POST') return reply({ error: 'Use POST' }, 405);
      if (!env.AI) return reply({ error: 'Add the Workers AI binding named AI to this worker' }, 500);
      if (!env.FIREBASE_SERVICE_ACCOUNT) return reply({ error: 'FIREBASE_SERVICE_ACCOUNT is not set on the worker' }, 500);
      try { return await handleListen(request, env, reply); }
      catch (e) { return aiFail(e, reply); }
    }

    // ---- call servers for in-app video calls: GET /ice ----
    if (new URL(request.url).pathname.replace(/\/+$/, '') === '/ice') {
      if (!originOk) return reply({ error: 'This website is not in ALLOWED_ORIGINS' }, 403);
      const stun = [{ urls: ['stun:stun.cloudflare.com:3478', 'stun:stun.l.google.com:19302'] }];
      const fixed = fixedTurn(env);
      if (!env.TURN_KEY_ID || !env.TURN_KEY_API_TOKEN) return reply({ iceServers: stun.concat(fixed), turn: fixed.length > 0 });
      try {
        const t = await fetch(`https://rtc.live.cloudflare.com/v1/turn/keys/${env.TURN_KEY_ID}/credentials/generate-ice-servers`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${env.TURN_KEY_API_TOKEN}`, 'content-type': 'application/json' },
          body: JSON.stringify({ ttl: 86400 })
        });
        if (!t.ok) return reply({ iceServers: stun.concat(fixed), turn: fixed.length > 0, error: `TURN ${t.status}` });
        const j = await t.json();
        const list = (Array.isArray(j.iceServers) ? j.iceServers : [j.iceServers]).filter(Boolean)
          .map(x => ({ ...x, urls: [].concat(x.urls || []).filter(u => !/:53(\?|$)/.test(u)) })); // browsers block port 53
        return reply({ iceServers: list.concat(fixed), turn: true });
      } catch (e) {
        return reply({ iceServers: stun.concat(fixed), turn: fixed.length > 0, error: 'TURN unreachable' });
      }
    }
    if (request.method !== 'POST') return reply({ error: 'Healvio AI server is running. Use POST.' }, 405);
    if (!originOk) return reply({ error: 'This website is not in ALLOWED_ORIGINS' }, 403);
    if (!env.ANTHROPIC_API_KEY && !env.AI) return reply({ error: 'AI is not set up: add the Workers AI binding named AI (free) or ANTHROPIC_API_KEY' }, 500);

    // only signed-in Healvio users can use the AI (protects your free daily allowance)
    if (env.FIREBASE_SERVICE_ACCOUNT) {
      try { await verifyIdToken((request.headers.get('authorization') || '').replace(/^Bearer\s+/i, ''), serviceAccount(env).project_id); }
      catch (e) { return reply({ error: 'Not signed in' }, 401); }
    }

    let body;
    try { body = await request.json(); } catch { return reply({ error: 'Bad JSON' }, 400); }
    const prompt = typeof body.prompt === 'string' ? body.prompt.slice(0, 120000) : '';
    if (!prompt) return reply({ error: 'Empty prompt' }, 400);

    if (!env.ANTHROPIC_API_KEY) {
      try { const out = await cfText(env, prompt, body.tier); return reply({ text: out.text, model: out.model, truncated: false }); }
      catch (e) { return aiFail(e, reply); }
    }

    const model = body.tier === 'quick' ? (env.QUICK_MODEL || 'claude-haiku-5-5') : (env.MODEL || 'claude-sonnet-5-5');
    const r = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'x-api-key': env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
      },
      body: JSON.stringify({ model, max_tokens: 4000, messages: [{ role: 'user', content: prompt }] })
    });

    if (r.status === 429) return reply({ error: 'rate_limited' }, 429);
    if (!r.ok) {
      const detail = (await r.text()).slice(0, 500);
      return reply({ error: `Claude API error ${r.status}`, detail }, 502);
    }
    const data = await r.json();
    const text = (data.content || []).filter(b => b.type === 'text').map(b => b.text).join('');
    return reply({ text, truncated: data.stop_reason === 'max_tokens' });
  }
};

/* ================= phone notifications =================
 * 1. Checks the sender is a signed-in Healvio user (Firebase ID token).
 * 2. Reads the alert (notifications/{id}) or ringing call (calls/{id}) they created.
 * 3. Sends it once to every phone of the recipient (pushTokens/{uid}) through
 *    Firebase Cloud Messaging. Phones that uninstalled are removed. */
const enc = new TextEncoder(), dec = new TextDecoder();
const b64uBytes = s => { s = String(s).replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '='; const b = atob(s), u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u; };
const bytesB64u = buf => { const u = new Uint8Array(buf); let s = ''; for (let i = 0; i < u.length; i++) s += String.fromCharCode(u[i]); return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); };
const strB64u = t => bytesB64u(enc.encode(t));
const RSA = { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' };
const FS = pid => `https://firestore.googleapis.com/v1/projects/${pid}/databases/(default)/documents/`;
const safeId = x => String(x || '').replace(/[^\w-]/g, '').slice(0, 128);

let saRaw = '', sa = null, saKey = null, gTok = { v: '', exp: 0 }, jwks = { keys: [], exp: 0 };
function serviceAccount(env) {
  if (env.FIREBASE_SERVICE_ACCOUNT !== saRaw) { sa = JSON.parse(env.FIREBASE_SERVICE_ACCOUNT); saRaw = env.FIREBASE_SERVICE_ACCOUNT; saKey = null; gTok = { v: '', exp: 0 }; }
  if (!sa.project_id || !sa.client_email || !sa.private_key) throw new Error('incomplete service account');
  return sa;
}
async function getJwks(force) {
  if (!force && jwks.keys.length && jwks.exp > Date.now()) return jwks.keys;
  const r = await fetch('https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com');
  const j = await r.json(), m = /max-age=(\d+)/.exec(r.headers.get('cache-control') || '');
  jwks = { keys: j.keys || [], exp: Date.now() + (m ? +m[1] * 1000 : 3600e3) };
  return jwks.keys;
}
async function verifyIdToken(token, pid) {
  const p = String(token || '').split('.');
  if (p.length !== 3) throw new Error('no token');
  const head = JSON.parse(dec.decode(b64uBytes(p[0]))), body = JSON.parse(dec.decode(b64uBytes(p[1])));
  if (head.alg !== 'RS256') throw new Error('bad alg');
  let jwk = (await getJwks()).find(k => k.kid === head.kid);
  if (!jwk) jwk = (await getJwks(true)).find(k => k.kid === head.kid);
  if (!jwk) throw new Error('unknown key');
  const key = await crypto.subtle.importKey('jwk', { kty: 'RSA', n: jwk.n, e: jwk.e, alg: 'RS256', ext: true }, RSA, false, ['verify']);
  const ok = await crypto.subtle.verify(RSA, key, b64uBytes(p[2]), enc.encode(p[0] + '.' + p[1]));
  const t = Math.floor(Date.now() / 1000);
  if (!ok || body.aud !== pid || body.iss !== 'https://securetoken.google.com/' + pid || !body.sub || body.exp < t || body.iat > t + 300) throw new Error('invalid token');
  return body.sub;
}
async function googleToken(s) {
  if (gTok.v && gTok.exp > Date.now() + 60e3) return gTok.v;
  if (!saKey) saKey = await crypto.subtle.importKey('pkcs8', b64uBytes(s.private_key.replace(/-----[^-]+-----/g, '').replace(/\s+/g, '')), RSA, false, ['sign']);
  const iat = Math.floor(Date.now() / 1000);
  const unsigned = strB64u(JSON.stringify({ alg: 'RS256', typ: 'JWT', kid: s.private_key_id })) + '.' + strB64u(JSON.stringify({
    iss: s.client_email, aud: 'https://oauth2.googleapis.com/token', iat, exp: iat + 3600,
    scope: 'https://www.googleapis.com/auth/firebase.messaging https://www.googleapis.com/auth/datastore'
  }));
  const jwt = unsigned + '.' + bytesB64u(await crypto.subtle.sign(RSA, saKey, enc.encode(unsigned)));
  const r = await fetch('https://oauth2.googleapis.com/token', { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: 'grant_type=' + encodeURIComponent('urn:ietf:params:oauth:grant-type:jwt-bearer') + '&assertion=' + jwt });
  const j = await r.json();
  if (!j.access_token) throw new Error('Google sign-in for the service account failed: ' + (j.error_description || j.error || r.status));
  gTok = { v: j.access_token, exp: Date.now() + (j.expires_in || 3600) * 1000 };
  return gTok.v;
}
function fromValue(v) {
  if (!v) return null;
  if ('stringValue' in v) return v.stringValue;
  if ('integerValue' in v) return Number(v.integerValue);
  if ('doubleValue' in v) return v.doubleValue;
  if ('booleanValue' in v) return v.booleanValue;
  if ('mapValue' in v) return fromFields(v.mapValue.fields);
  if ('arrayValue' in v) return (v.arrayValue.values || []).map(fromValue);
  return null;
}
const fromFields = f => { const o = {}; for (const k of Object.keys(f || {})) o[k] = fromValue(f[k]); return o; };
async function fsGet(pid, tok, path) {
  const r = await fetch(FS(pid) + path, { headers: { authorization: 'Bearer ' + tok } });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error('Firestore read ' + r.status);
  return fromFields((await r.json()).fields);
}
async function fsList(pid, tok, col) {
  const r = await fetch(FS(pid) + col + '?pageSize=100', { headers: { authorization: 'Bearer ' + tok } });
  if (!r.ok) return [];
  return ((await r.json()).documents || []).map(d => d.name.split('/').pop());
}
// creates pushLog/{key}; false if it already exists → the alert was sent before
async function fsCreateOnce(pid, tok, key, at, lenient) {
  let r;
  try {
    r = await fetch(FS(pid) + 'pushLog?documentId=' + encodeURIComponent(key), { method: 'POST',
      headers: { authorization: 'Bearer ' + tok, 'content-type': 'application/json' }, body: JSON.stringify({ fields: { at: { integerValue: String(at) } } }) });
  } catch (e) { return !!lenient; }
  if (r.ok) return true;
  // 409 = this alert was sent before. Any other problem (busy database, free limit) stops only the
  // timed reminders (so they never repeat); an alert a person just sent still goes out.
  return r.status !== 409 && !!lenient;
}
async function fsSetTokens(pid, tok, uid, tokens) {
  await fetch(FS(pid) + 'pushTokens/' + uid + '?updateMask.fieldPaths=tokens', { method: 'PATCH',
    headers: { authorization: 'Bearer ' + tok, 'content-type': 'application/json' },
    body: JSON.stringify({ fields: { tokens: { arrayValue: { values: tokens.map(t => ({ stringValue: t })) } } } }) });
}
async function fcmSend(pid, tok, token, data, ttl) {
  const r = await fetch(`https://fcm.googleapis.com/v1/projects/${pid}/messages:send`, { method: 'POST',
    headers: { authorization: 'Bearer ' + tok, 'content-type': 'application/json' },
    body: JSON.stringify({ message: { token, data, webpush: { headers: { Urgency: 'high', TTL: String(ttl) } } } }) });
  if (r.ok) return 'ok';
  const t = await r.text().catch(() => '');
  if (r.status === 404 || /UNREGISTERED/.test(t)) return 'gone';
  let why = '';
  try { const j = JSON.parse(t).error || {}; why = ((j.details || []).map(d => d.errorCode).filter(Boolean)[0] || j.status || '') + ' ' + (j.message || ''); } catch (e) { why = t; }
  return 'error ' + r.status + ' ' + String(why).trim().slice(0, 160);
}
// the phone asks for the alert at the same moment it saves it: wait a little for it to arrive
async function fsGetSoon(pid, tok, path, info) {
  for (let i = 0; i < 7; i++) {
    const d = await fsGet(pid, tok, path).catch(e => { if (info) info.err = String((e && e.message) || e); return null; });
    if (d) return d;
    if (info && /\b(429|403|401)\b/.test(info.err || '')) return null; // no point waiting
    await new Promise(r => setTimeout(r, 150 + i * 150));
  }
  return null;
}
async function handlePush(request, env, reply) {
  if (request.method !== 'POST') return reply({ error: 'Use POST' }, 405);
  if (!env.FIREBASE_SERVICE_ACCOUNT) return reply({ error: 'FIREBASE_SERVICE_ACCOUNT is not set on the worker' }, 500);
  let s;
  try { s = serviceAccount(env); } catch (e) { return reply({ error: 'FIREBASE_SERVICE_ACCOUNT is not the right JSON file' }, 500); }
  const pid = s.project_id;
  // check the sender, read the request and get Google access at the same time (faster)
  const tokP = googleToken(s);
  tokP.catch(() => {});
  let me, body;
  try { [me, body] = await Promise.all([verifyIdToken((request.headers.get('authorization') || '').replace(/^Bearer\s+/i, ''), pid), request.json().catch(() => null)]); }
  catch (e) { return reply({ error: 'Not signed in' }, 401); }
  if (!body) return reply({ error: 'Bad JSON' }, 400);
  let tok;
  try { tok = await tokP; } catch (e) { return reply({ error: 'google_login', detail: String((e && e.message) || e).slice(0, 200) }, 502); }
  const now = Date.now(), info = {};
  // why an alert could not be found: the database's free daily limit, or no access
  const dbErr = () => /429/.test(info.err || '') ? reply({ sent: 0, error: 'free_limit' }) : info.err ? reply({ sent: 0, error: 'database', detail: info.err }) : null;
  let to = [], data, ttl, key;
  // look up the other person's phone while the alert is being checked (saves a round trip)
  const hint = safeId(body.to || ''), pre = {};
  if (hint && hint !== 'admin') pre[hint] = fsGet(pid, tok, 'pushTokens/' + hint).catch(() => null);
  if (body.call) {
    const c = await fsGetSoon(pid, tok, 'calls/' + safeId(body.call), info);
    if (!c && info.err) return dbErr();
    if (!c || c.from !== me || c.status !== 'ringing' || Math.abs(now - (c.createdAt || 0)) > 120000) return reply({ sent: 0, skipped: 'not a ringing call of yours' });
    const n = Math.min(12, Math.max(1, parseInt(body.n, 10) || 1)); // the caller rings again every few seconds
    to = [c.to]; key = 'call-' + safeId(c.id) + '-' + n; ttl = 30;
    data = { kind: 'call', tag: 'call-' + safeId(c.id), url: './?go=room&id=' + encodeURIComponent(safeId(c.rid)),
      title: (c.kind === 'audio' ? '📞 Incoming voice call' : '📹 Incoming video call'),
      body: String(c.fromName || 'Someone').slice(0, 80) + ' is calling you. Tap to answer.' };
  } else if (body.callEnd) {
    const c = await fsGet(pid, tok, 'calls/' + safeId(body.callEnd));
    if (!c || c.from !== me || !['cancelled', 'missed'].includes(c.status) || Math.abs(now - (c.createdAt || 0)) > 600000) return reply({ sent: 0, skipped: 'not a missed call of yours' });
    to = [c.to]; key = 'callend-' + safeId(c.id); ttl = 86400;
    data = { kind: 'callend', tag: 'call-' + safeId(c.id), url: './?go=room&id=' + encodeURIComponent(safeId(c.rid)),
      title: (c.kind === 'audio' ? '📞 Missed voice call' : '📹 Missed video call'),
      body: String(c.fromName || 'Someone').slice(0, 80) + ' called you. Tap to open the consultation.' };
  } else if (body.id) {
    const n = await fsGetSoon(pid, tok, 'notifications/' + safeId(body.id), info);
    if (!n && info.err) return dbErr();
    if (!n || n.from !== me || Math.abs(now - (n.at || 0)) > 600000) return reply({ sent: 0, skipped: 'not a recent alert of yours' });
    to = n.to === 'admin' ? await fsList(pid, tok, 'admins') : [n.to];
    key = 'n-' + safeId(n.id); ttl = 86400;
    data = noteData(n);
  } else return reply({ error: 'Nothing to send' }, 400);
  // mark as sent and look up the phones at the same time, then send to every phone at once
  const users = [...new Set(to.map(safeId).filter(Boolean))].slice(0, 25);
  const [fresh, recs] = await Promise.all([fsCreateOnce(pid, tok, key, now, true), Promise.all(users.map(u => pre[u] || fsGet(pid, tok, 'pushTokens/' + u).catch(() => null)))]);
  if (!fresh) return reply({ sent: 0, skipped: 'already sent' });
  let sent = 0, phones = 0, gone = 0, fcm = '';
  await Promise.all(users.map(async (u, i) => {
    const rec = recs[i];
    const tokens = rec && Array.isArray(rec.tokens) ? rec.tokens.filter(t => typeof t === 'string' && t).slice(-5) : [];
    phones += tokens.length;
    const res = await Promise.all(tokens.map(t => fcmSend(pid, tok, t, data, ttl).catch(e => 'error ' + String((e && e.message) || e).slice(0, 120))));
    sent += res.filter(r => r === 'ok').length;
    const dead = tokens.filter((t, k) => res[k] === 'gone');
    gone += dead.length;
    if (!fcm) fcm = res.find(r => r !== 'ok' && r !== 'gone') || '';
    if (dead.length) await fsSetTokens(pid, tok, u, tokens.filter(t => !dead.includes(t))).catch(() => {});
  }));
  const out = { sent, phones };
  if (gone) out.gone = gone;
  if (fcm && !sent) out.fcm = fcm;
  return reply(out);
}

// what a saved alert looks like on the phone
const NOTE_TITLES = { room: 'Consultation', consult: 'Consultation', rxView: 'Prescription', order: 'Medicine order', sOrders: 'Medicine orders', pStores: 'Medicine order', aDoctor: 'Admin', aMore: 'Admin', accStatus: 'Your account', pHome: 'Medicines', pDoctor: 'Reviews' };
function noteData(n) {
  const ref = n.ref || {};
  const t0 = typeof n.title === 'string' && n.title.trim() ? n.title.trim().slice(0, 60) : (NOTE_TITLES[ref.view] || 'Healvio');
  return { kind: n.kind === 'urgent' ? 'urgent' : 'alert', tag: 'n-' + safeId(n.id), title: (n.kind === 'urgent' ? '🔔 ' : '') + 'Healvio · ' + t0,
    body: String(n.text || '').slice(0, 600),
    url: n.to === 'admin' ? './' : ref.view ? './?go=' + encodeURIComponent(safeId(ref.view)) + (ref.id ? '&id=' + encodeURIComponent(safeId(ref.id)) : '') : './?go=alerts' };
}

/* ================= free AI on Cloudflare Workers AI ================= */
const SYS = 'You are a careful assistant inside Healvio, a telemedicine app. Follow the instructions exactly. Never invent medical facts that are not in the text you are given. When asked for JSON, reply with valid JSON only, with no extra words.';
// System check: does each part of the worker really work right now? (signed-in people only)
async function healthCheck(request, env) {
  const out = {}, txt = e => String((e && (e.message || e)) || e || '').slice(0, 220);
  const limit = (p, ms) => Promise.race([p, new Promise((_, no) => setTimeout(() => no(new Error('no answer in ' + ms / 1000 + ' s')), ms))]);
  let s = null;
  if (!env.FIREBASE_SERVICE_ACCOUNT) out.google = 'missing';
  else { try { s = serviceAccount(env); } catch (e) { out.google = 'FIREBASE_SERVICE_ACCOUNT is not the right JSON file'; } }
  if (s) {
    try { await verifyIdToken((request.headers.get('authorization') || '').replace(/^Bearer\s+/i, ''), s.project_id); }
    catch (e) { return { error: 'sign in' }; }
  }
  await Promise.all([
    (async () => {
      if (!s) return;
      let tok;
      try { tok = await limit(googleToken(s), 8000); out.google = 'ok'; } catch (e) { out.google = txt(e); return; }
      try { await limit(fsGet(s.project_id, tok, 'system/cron'), 8000); out.db = 'ok'; } catch (e) { out.db = /\b429\b/.test(txt(e)) ? 'free_limit' : txt(e); }
    })(),
    (async () => {
      if (!payOn(env)) { out.paypal = 'missing'; return; }
      try { await limit(paypalToken(env), 8000); out.paypal = 'ok'; } catch (e) { out.paypal = txt(e); }
    })(),
    (async () => {
      if (!env.AI) { out.ai = 'missing'; return; }
      try { await limit(env.AI.run(env.AI_MODEL || '@cf/meta/llama-3.3-70b-instruct-fp8-fast', { messages: [{ role: 'user', content: 'Reply with the word OK.' }], max_tokens: 3 }), 15000); out.ai = 'ok'; }
      catch (e) { out.ai = isQuota(e) ? 'free_limit' : txt(e); }
    })()
  ]);
  return out;
}
const isQuota = e => /3036|daily free allocation|neurons|quota/i.test(String((e && (e.message || e)) || ''));
function aiFail(e, reply) {
  if (isQuota(e)) return reply({ error: 'free_limit' }, 429);
  return reply({ error: 'AI error', detail: String((e && (e.message || e)) || '').slice(0, 300) }, 502);
}
function pickText(out) {
  if (!out) return '';
  if (typeof out === 'string') return out;
  const r = out.response !== undefined ? out.response : out.result && out.result.response;
  if (typeof r === 'string') return r;
  if (r && typeof r === 'object') return JSON.stringify(r);
  const ch = out.choices && out.choices[0];
  if (ch && ch.message && typeof ch.message.content === 'string') return ch.message.content;
  if (Array.isArray(out.output)) {
    return out.output.filter(o => o && o.type === 'message').flatMap(o => o.content || []).map(c => c.text || '').join('');
  }
  return '';
}
async function cfText(env, prompt, tier) {
  const smart = env.AI_MODEL || '@cf/meta/llama-3.3-70b-instruct-fp8-fast';
  const quick = env.AI_QUICK_MODEL || '@cf/meta/llama-3.1-8b-instruct-fp8';
  const chain = [...new Set(tier === 'quick' ? [quick, smart] : [smart, '@cf/meta/llama-4-scout-17b-16e-instruct', quick])];
  let last;
  for (const m of chain) {
    try {
      const out = await env.AI.run(m, { messages: [{ role: 'system', content: SYS }, { role: 'user', content: prompt.slice(0, 60000) }], max_tokens: 2500, temperature: 0.2 });
      const text = pickText(out).trim();
      if (text) return { text, model: m };
      last = new Error('empty answer from ' + m);
    } catch (e) { if (isQuota(e)) throw e; last = e; }
  }
  throw last || new Error('AI gave no answer');
}
// Whisper often "hears" these in silence
const NOISE = /^\W*(thank you( (so|very) much)?|thanks|thanks for watching|thank you for watching|please subscribe|subscribe to (my|the) channel|like and subscribe|(hi|hey|hello),? (guys|everyone)( and welcome back)?|welcome back( to (my|the) channel)?|see you (next time|in the next (video|one))|you|bye|okay|ok|hmm+|uh+|um+)?\W*$/i;
async function handleListen(request, env, reply) {
  const s = serviceAccount(env), pid = s.project_id;
  const tokP = googleToken(s); tokP.catch(() => {});
  let me, body;
  try { [me, body] = await Promise.all([verifyIdToken((request.headers.get('authorization') || '').replace(/^Bearer\s+/i, ''), pid), request.json().catch(() => null)]); }
  catch (e) { return reply({ error: 'Not signed in' }, 401); }
  if (!body || typeof body.audio !== 'string' || body.audio.length < 800 || body.audio.length > 3500000) return reply({ error: 'Bad audio' }, 400);
  const r = await fsGet(pid, await tokP, 'requests/' + safeId(body.rid));
  if (!r || (r.doctorId !== me && r.patientId !== me) || r.status !== 'live') return reply({ error: 'Not your live consultation' }, 403);
  const model = '@cf/openai/whisper-large-v3-turbo';
  const ctx = await listenContext(pid, await tokP, r);
  const prev = typeof body.prev === 'string' ? body.prev.replace(/\s+/g, ' ').trim().slice(-180) : '';
  const lang = /^[a-z]{2}$/.test(String(body.lang || '')) && WHISPER_LANGS.includes(body.lang) ? body.lang : '';
  const opts = { audio: body.audio, task: 'transcribe', vad_filter: true, initial_prompt: (ctx + (prev ? ' ' + prev : '')).slice(-900) };
  if (lang) opts.language = lang;
  let out;
  try { out = await env.AI.run(model, opts); }
  catch (e) { if (isQuota(e)) throw e; out = await env.AI.run(model, { audio: body.audio, ...(lang ? { language: lang } : {}) }); }
  let heard = langCode((out && out.transcription_info && out.transcription_info.language) || lang || '');
  let text = cleanSpeech(out);
  // Whisper sometimes "hears" Indian speech as Icelandic, Welsh, Nordic and so on. Healvio is used in
  // English and Indian languages only: anything else is heard again as English, and dropped if still foreign.
  if (!lang && text && ((heard && !WHISPER_LANGS.includes(heard)) || FOREIGN.test(text))) {
    let again = null;
    try { again = await env.AI.run(model, { ...opts, language: 'en' }); } catch (e) { if (isQuota(e)) throw e; }
    text = again ? cleanSpeech(again) : '';
    heard = 'en';
  }
  if (FOREIGN.test(text)) text = '';
  return reply({ text: text.slice(0, 2000), lang: heard });
}
// Whisper may name the language ("english") or give its code ("en")
const LANG_NAMES = { english: 'en', hindi: 'hi', telugu: 'te', tamil: 'ta', kannada: 'kn', malayalam: 'ml', marathi: 'mr', bengali: 'bn', gujarati: 'gu', punjabi: 'pa', urdu: 'ur', oriya: 'or', odia: 'or', assamese: 'as', nepali: 'ne', sanskrit: 'sa' };
const langCode = l => { const k = String(l || '').trim().toLowerCase(); return LANG_NAMES[k] || k; };
// letters of languages Healvio is not used in (accented Latin, Greek, Cyrillic, Hebrew, Thai, Chinese, Japanese, Korean)
const FOREIGN = /[\u00C0-\u024F\u0370-\u03FF\u0400-\u04FF\u0590-\u05FF\u0E00-\u0E7F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]/;
const WHISPER_LANGS = ['en', 'hi', 'te', 'ta', 'kn', 'ml', 'mr', 'bn', 'gu', 'pa', 'ur', 'or', 'as', 'ne', 'sa'];
// medical words help speech-to-text spell medicines and symptoms correctly
const ctxCache = new Map();
async function listenContext(pid, tok, r) {
  const key = r.id || r.doctorId, hit = ctxCache.get(key);
  if (hit && hit.exp > Date.now()) return hit.v;
  let d = null, rx = null;
  try { [d, rx] = await Promise.all([fsGet(pid, tok, 'public/' + safeId(r.doctorId)).catch(() => null), r.rxId ? fsGet(pid, tok, 'prescriptions/' + safeId(r.rxId)).catch(() => null) : null]); } catch (e) {}
  const doc = (d && d.doc) || {};
  const meds = rx && Array.isArray(rx.medicines) ? rx.medicines.map(m => m && m.name).filter(Boolean).slice(0, 12).join(', ') : '';
  const v = `Medical consultation between a doctor and a patient in India${doc.system ? ' (' + doc.system + (doc.specialization ? ', ' + doc.specialization : '') + ')' : ''}. ` +
    `Patient's problem: ${String(r.problem || '').replace(/\s+/g, ' ').slice(0, 160)}.` + (meds ? ` Medicines: ${meds}.` : '') +
    ' Words like fever, cough, BP, sugar, tablet, syrup, mg, 1-0-1, after food, before food, twice a day.';
  ctxCache.set(key, { v, exp: Date.now() + 10 * 60000 });
  if (ctxCache.size > 200) ctxCache.delete(ctxCache.keys().next().value);
  return v;
}
// keep only real speech: drop silent or made-up pieces and stuck repeats
function cleanSpeech(out) {
  let parts = Array.isArray(out && out.segments) && out.segments.length ? out.segments : null;
  let text;
  if (parts) {
    text = parts.filter(sg => sg && typeof sg.text === 'string')
      .filter(sg => !((+sg.no_speech_prob > 0.6 && +sg.avg_logprob < -1) || +sg.compression_ratio > 2.6 || +sg.avg_logprob < -1.6))
      .map(sg => sg.text.trim()).filter(t => t && !NOISE.test(t)).join(' ');
  } else text = String((out && (out.text || (out.result && out.result.text))) || '');
  text = text.replace(/\s+/g, ' ').trim();
  // "fine fine fine fine" → "fine"; a phrase repeated 3+ times in a row → once
  for (let n = 6; n >= 1; n--) {
    const re = new RegExp('((?:\\S+\\s+){' + (n - 1) + '}\\S+)(?:\\s+\\1){2,}', 'gi');
    text = text.replace(re, '$1');
  }
  return NOISE.test(text) ? '' : text;
}

/* ================= AI consultation summary =================
 * Reads the whole consultation (chat + what each person said on the call + prescription),
 * pulls out the facts in steps for long calls, then checks every point against the conversation
 * before saving. Uses only what the doctor and patient said. */
const SUM_SCHEMA = '{"summary":"4-6 simple sentences","chief_complaint":"","symptoms":["symptom with how long, as the patient said"],"history":["past illness, allergies, current medicines mentioned"],"doctor_findings":["what the doctor observed or concluded"],"diagnosis":"diagnosis the doctor said, or empty","medicines":[{"name":"","dose":"","timing":"","days":"","instructions":""}],"tests":["tests or scans the doctor asked for"],"key_points":["other important things the doctor said"],"lifestyle":["food, rest, exercise or habit advice from the doctor"],"instant_relief":["quick relief the doctor suggested"],"warning_signs":["signs the doctor said need urgent care"],"hospital_visit":"what the doctor said about visiting a hospital, or empty","follow_up":"follow-up the doctor asked for, or empty","doubts_clarified":[{"question":"","answer":""}],"open_questions":["questions the patient asked that were not answered"],"doctor_note":{"s":"subjective","o":"objective","a":"assessment","p":"plan"}}';
const SUM_RULES = 'STRICT RULES: (1) Use ONLY what the doctor and the patient said below and what is written in the prescription. Never add a diagnosis, medicine, dose, test or advice of your own. ' +
  '(2) Lines marked "on call" come from automatic speech-to-text and may have small errors: if a spoken medicine name sounds like one in the prescription, use the prescription spelling. ' +
  '(3) The prescription is the final word for medicine names, doses, timing and days. Include every prescription medicine. Add a medicine said only in the conversation with instructions "said on the call". ' +
  '(4) Never guess numbers. If the doctor did not mention something, use an empty string or an empty list. ' +
  '(5) "instant_relief", "warning_signs", "hospital_visit" and "follow_up" must come only from the doctor. ' +
  '(6) "doctor_note" is a short clinical SOAP note in English for the doctor. ';
async function aiJson(env, prompt, maxTokens) {
  const chain = [env.AI_MODEL || '@cf/meta/llama-3.3-70b-instruct-fp8-fast', '@cf/meta/llama-4-scout-17b-16e-instruct'];
  let last;
  for (const m of chain) {
    for (let k = 0; k < 2; k++) {
      try {
        const out = await env.AI.run(m, { messages: [{ role: 'system', content: SYS }, { role: 'user', content: prompt }], max_tokens: maxTokens || 3000, temperature: 0.1 });
        const raw = out && typeof out.response === 'object' && out.response ? JSON.stringify(out.response) : pickText(out);
        const j = jsonIn(raw);
        if (j) return j;
        last = new Error('not JSON from ' + m);
      } catch (e) { if (isQuota(e)) throw e; last = e; }
    }
  }
  throw last || new Error('AI gave no answer');
}
// "-", "N/A", "not mentioned" … mean nothing was said: keep them empty
const BLANK = /^[\s\-–—.:]*$|^\s*(n\/?a|none|nil|null|not mentioned|not specified|not given|not discussed|unknown|no information)\s*[.!]?\s*$/i;
const strL = (a, n) => (Array.isArray(a) ? a : []).map(x => typeof x === 'string' ? x.trim() : x && typeof x === 'object' ? Object.values(x).filter(v => typeof v === 'string').join(' – ') : '').filter(x => x && !BLANK.test(x)).slice(0, n || 20).map(x => x.slice(0, 400));
const strS = (v, n) => typeof v === 'string' && !BLANK.test(v) ? v.trim().slice(0, n || 800) : '';
function cleanSummary(o, lang) {
  o = o && typeof o === 'object' ? o : {};
  const meds = (Array.isArray(o.medicines) ? o.medicines : []).filter(m => m && typeof m === 'object' && strS(m.name)).slice(0, 25)
    .map(m => ({ name: strS(m.name, 120), dose: strS(m.dose, 60), timing: strS(m.timing || m.freq, 80), days: strS(String(m.days == null ? '' : m.days), 40), instructions: strS(m.instructions || m.note, 160) }));
  const dc = (Array.isArray(o.doubts_clarified) ? o.doubts_clarified : []).filter(q => q && strS(q.question)).slice(0, 10).map(q => ({ question: strS(q.question, 300), answer: strS(q.answer, 500) }));
  const dn = o.doctor_note && typeof o.doctor_note === 'object' ? o.doctor_note : {};
  return { summary: strS(o.summary, 1500), chief_complaint: strS(o.chief_complaint, 300), symptoms: strL(o.symptoms), history: strL(o.history), doctor_findings: strL(o.doctor_findings),
    diagnosis: strS(o.diagnosis, 300), medicines: meds, tests: strL(o.tests), key_points: strL(o.key_points), lifestyle: strL(o.lifestyle), instant_relief: strL(o.instant_relief),
    warning_signs: strL(o.warning_signs), hospital_visit: strS(o.hospital_visit, 400), follow_up: strS(o.follow_up, 400), doubts_clarified: dc, open_questions: strL(o.open_questions, 10),
    doctor_note: { s: strS(dn.s, 600), o: strS(dn.o, 600), a: strS(dn.a, 600), p: strS(dn.p, 800) }, lang: lang || 'English' };
}
// headings shown in the app, translated with the summary so the whole page is in one language
const SUM_LABELS = { simple: 'In simple words', main: 'Main problem', symptoms: 'Symptoms you told the doctor', history: 'Health history mentioned', found: 'What the doctor found',
  medicines: 'Your medicines', tests: 'Tests to do', points: 'Important points from the doctor', food: 'Food, rest & habits', doubts: 'Doubts clarified',
  relief: 'Instant relief (as suggested by the doctor)', warning: 'Go to a hospital quickly if', hospital: 'Hospital visit', followup: 'Follow-up', open: 'Still unanswered — ask your doctor',
  none: 'Not mentioned by the doctor.', days: 'days', listen: 'Listen to this summary' };
// the summary is written and checked in English (most accurate), then every part is translated
async function translateSummary(env, s, lang) {
  const groups = [
    { summary: s.summary, chief_complaint: s.chief_complaint, diagnosis: s.diagnosis, symptoms: s.symptoms, history: s.history, doctor_findings: s.doctor_findings },
    { medicines: s.medicines.map(m => ({ timing: m.timing, days: m.days, instructions: m.instructions })), tests: s.tests, key_points: s.key_points, lifestyle: s.lifestyle, instant_relief: s.instant_relief },
    { warning_signs: s.warning_signs, hospital_visit: s.hospital_visit, follow_up: s.follow_up, doubts_clarified: s.doubts_clarified, open_questions: s.open_questions, labels: SUM_LABELS }
  ];
  const ask = g => aiJson(env, `Translate every text value in this JSON from English into ${lang}, in simple everyday words that a patient in India understands. ` +
    `Keep exactly the same JSON keys, the same number of items in every list and the same order. Do not add, remove or change any information. ` +
    `Keep medicine names, doses (mg, ml, tablets), numbers, dates and codes like 1-0-1 exactly as written, and also write what a code means in ${lang} words (for example 1-0-1 means morning and night). ` +
    `Translate every value, including short ones. Reply with only the JSON.\n\n${JSON.stringify(g)}`, 3500);
  const res = await Promise.all(groups.map(g => ask(g).catch(e => { if (isQuota(e)) throw e; return null; })));
  const out = { ...s, labels: { ...SUM_LABELS } };
  let done = 0;
  const str = (t, en) => typeof t === 'string' && t.trim() ? t.trim().slice(0, 1500) : en;
  const list = (t, en) => Array.isArray(t) && t.length === en.length ? en.map((x, i) => str(t[i], x)) : en;
  res.forEach((t, gi) => {
    if (!t || typeof t !== 'object') return;
    done++;
    for (const k of Object.keys(groups[gi])) {
      const en = out[k], v = t[k];
      if (k === 'labels') { if (v && typeof v === 'object') for (const lk of Object.keys(SUM_LABELS)) out.labels[lk] = str(v[lk], SUM_LABELS[lk]).slice(0, 120); }
      else if (k === 'medicines') { if (Array.isArray(v) && v.length === en.length) out.medicines = en.map((m, i) => ({ ...m, timing: str(v[i] && v[i].timing, m.timing), days: str(v[i] && v[i].days, m.days), instructions: str(v[i] && v[i].instructions, m.instructions) })); }
      else if (k === 'doubts_clarified') { if (Array.isArray(v) && v.length === en.length) out.doubts_clarified = en.map((q, i) => ({ question: str(v[i] && v[i].question, q.question), answer: str(v[i] && v[i].answer, q.answer) })); }
      else if (Array.isArray(en)) out[k] = list(v, en);
      else if (typeof en === 'string') out[k] = en ? str(v, en) : '';
    }
  });
  out.translated = done + '/3';
  if (!done) { out.lang = 'English'; delete out.labels; }
  return out;
}
async function fsMessages(pid, tok, rid) {
  const out = [];
  let after = null;
  for (let page = 0; page < 6; page++) {
    const q = { from: [{ collectionId: 'messages' }], orderBy: [{ field: { fieldPath: 'at' }, direction: 'ASCENDING' }], limit: 500 };
    if (after != null) q.startAt = { values: [{ integerValue: String(after) }], before: false };
    const r = await fetch(FS(pid) + 'requests/' + safeId(rid) + ':runQuery', { method: 'POST', headers: { authorization: 'Bearer ' + tok, 'content-type': 'application/json' }, body: JSON.stringify({ structuredQuery: q }) });
    const rows = r.ok ? await r.json() : [];
    const docs = (Array.isArray(rows) ? rows : []).filter(x => x && x.document).map(x => fromFields(x.document.fields));
    out.push(...docs);
    if (docs.length < 500) break;
    after = Number(docs[docs.length - 1].at) || 0;
  }
  return out;
}
function sumLines(r, msgs) {
  const t0 = Number(r.startedAt) || (msgs[0] && Number(msgs[0].at)) || 0;
  const clock = at => { const s = Math.max(0, Math.round(((Number(at) || t0) - t0) / 1000)); return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); };
  return msgs.filter(m => m && (m.text || m.image)).map(m => {
    const who = m.from === r.doctorId ? 'Doctor' : m.from === r.patientId ? 'Patient' : 'System';
    if (who === 'System' && !/start|end|call/i.test(String(m.text || ''))) return '';
    return `[${clock(m.at)}] ${who}${m.stt ? ' (on call)' : ''}: ${String(m.text || '').replace(/\s+/g, ' ').trim()}${m.image ? ' [shared a photo]' : ''}`;
  }).filter(Boolean);
}
function rxLines(rx) {
  if (!rx) return '(no prescription written)';
  const meds = (Array.isArray(rx.medicines) ? rx.medicines : []).filter(m => m && m.name).map(m => `- ${m.name} | dose: ${m.dose || '-'} | timing: ${m.freq || '-'} | days: ${m.days || '-'}${m.note ? ' | ' + m.note : ''}`).join('\n');
  return `Diagnosis: ${rx.diagnosis || '-'}\nMedicines:\n${meds || '-'}\nInstant relief: ${rx.relief || '-'}\nAdvice: ${rx.advice || '-'}\nHospital visit: ${rx.visit || '-'}\nFollow-up: ${rx.followUp || '-'}`;
}
async function handleSummary(request, env, reply) {
  const s = serviceAccount(env), pid = s.project_id;
  const tokP = googleToken(s); tokP.catch(() => {});
  let me, body;
  try { [me, body] = await Promise.all([verifyIdToken((request.headers.get('authorization') || '').replace(/^Bearer\s+/i, ''), pid), request.json().catch(() => null)]); }
  catch (e) { return reply({ error: 'Not signed in' }, 401); }
  if (!body || !body.rid) return reply({ error: 'Which consultation?' }, 400);
  const tok = await tokP, rid = safeId(body.rid);
  const r = await fsGet(pid, tok, 'requests/' + rid);
  if (!r || (r.doctorId !== me && r.patientId !== me)) return reply({ error: 'Not your consultation' }, 403);
  if (!['live', 'completed'].includes(r.status)) return reply({ error: 'The consultation has not started yet' }, 409);
  r.id = rid;
  const lang = /^[A-Za-z ]{2,20}$/.test(String(body.lang || '')) ? String(body.lang).trim() : 'English';
  const [msgs, d, p, rx] = await Promise.all([fsMessages(pid, tok, rid), fsGet(pid, tok, 'public/' + safeId(r.doctorId)).catch(() => null),
    fsGet(pid, tok, 'accounts/' + safeId(r.patientId)).catch(() => null), r.rxId ? fsGet(pid, tok, 'prescriptions/' + safeId(r.rxId)).catch(() => null) : null]);
  const lines = sumLines(r, msgs);
  const doc = (d && d.doc) || {};
  const about = `Consultation type: ${doc.system || ''}${doc.specialization ? ', ' + doc.specialization : ''}. Patient${p && p.age ? ', age ' + p.age : ''}${p && p.gender ? ', ' + p.gender : ''}. Patient's problem when booking: "${String(r.problem || '').slice(0, 600)}".`;
  const rxT = rxLines(rx);
  const lng = 'English';
  let source, steps = 0;
  const all = lines.join('\n');
  if (all.length <= 34000) source = 'Conversation (time from start, who spoke):\n' + (all || '(no messages)');
  else {
    // long consultation: take notes part by part, then write the summary from the notes
    const chunks = []; let cur = '';
    for (const l of lines) { if ((cur + l).length > 26000 && cur) { chunks.push(cur); cur = ''; } cur += l + '\n'; }
    if (cur) chunks.push(cur);
    const notes = [];
    for (const [i, c] of chunks.slice(0, 10).entries()) {
      const n = await aiJson(env, `${about}\nThis is part ${i + 1} of ${chunks.length} of a long doctor–patient consultation. Write precise notes of EVERY medical fact in this part: symptoms with duration, history, what the doctor examined or concluded, every medicine/dose/timing/days said, tests, advice, warnings, follow-up, and each question with its answer. ${SUM_RULES}Reply with only JSON: {"notes":["[time] who: fact"]}\n\n${c}`, 2500);
      steps++;
      notes.push(...strL(n && n.notes, 120).map(x => x.slice(0, 300)));
    }
    source = 'Notes taken from the whole consultation, in order:\n' + notes.join('\n');
  }
  const draft = await aiJson(env, `You are the AI assistant inside Healvio, a telemedicine app in India. Write an accurate summary of this consultation for the patient in ${lng}, in simple everyday words (doctor_note in English).\n${SUM_RULES}\nReply with only this JSON (fill what was said, leave the rest empty):\n${SUM_SCHEMA}\n\n${about}\n\n${source}\n\nDoctor's prescription:\n${rxT}`, 3500);
  steps++;
  let final = draft;
  try {
    const chk = await aiJson(env, `Check this AI summary of a doctor–patient consultation against the source below. Remove any point that the doctor or patient did not say and that is not in the prescription. Correct any wrong medicine name, dose, timing, number of days or date using the source. Add any important medicine, test, warning sign or follow-up that the source has but the summary missed. Keep the same JSON shape and the same language (${lng}).\n${SUM_RULES}\nReply with only the corrected JSON.\n\nSUMMARY:\n${JSON.stringify(draft).slice(0, 12000)}\n\n${about}\n\n${source}\n\nDoctor's prescription:\n${rxT}`, 3500);
    steps++;
    if (chk && typeof chk.summary === 'string' && chk.summary.trim()) final = chk;
  } catch (e) { if (isQuota(e) && !draft) throw e; }
  let out = { ...cleanSummary(final, 'English'), at: Date.now(), by: me === r.doctorId ? 'doctor' : 'patient', rxId: r.rxId || '', lines: lines.length, steps };
  if (!out.summary) return reply({ error: 'AI could not summarize this consultation. Please try again.' }, 502);
  if (lang !== 'English') { out = await translateSummary(env, out, lang); out.lang = out.translated === '0/3' ? 'English' : lang; out.steps = steps + 1; }
  await fsPatch(pid, tok, 'requests/' + rid, { aiSummary: out });
  // tell the patient when the doctor's phone asked for it
  if (body.notify && me === r.doctorId && r.patientId) {
    const nid = 'nsum' + rid.slice(0, 40) + (r.rxId ? safeId(r.rxId).slice(0, 20) : '');
    const text = '📝 Your consultation summary is ready: what the doctor said, your medicines and when to follow up.';
    try {
      await fetch(FS(pid) + 'notifications?documentId=' + encodeURIComponent(nid), { method: 'POST', headers: { authorization: 'Bearer ' + tok, 'content-type': 'application/json' },
        body: JSON.stringify({ fields: toFields({ id: nid, to: r.patientId, text, ref: { view: 'consult', id: rid }, kind: 'info', at: Date.now(), read: false, from: me }) }) });
      if (await fsCreateOnce(pid, tok, 'n-' + nid, Date.now())) await pushTo(pid, tok, r.patientId, { kind: 'alert', tag: 'n-' + nid, title: 'Healvio · Consultation summary', body: text, url: './?go=consult&id=' + encodeURIComponent(rid) }, 86400);
    } catch (e) {}
  }
  return reply({ summary: out });
}

/* ================= PayPal payments =================
 * 1. The phone asks /pay/create → this worker reads the real price from the database
 *    (doctor's fee, or the total the store entered) and opens a PayPal order for it.
 * 2. The patient approves in PayPal's own window (Healvio never sees card or PayPal password).
 * 3. The phone asks /pay/capture → this worker collects the money, checks the order really is
 *    for this consultation/order and for the full amount, then marks it paid in the database. */
const payOn = env => !!(env.PAYPAL_CLIENT_ID && env.PAYPAL_CLIENT_SECRET && env.FIREBASE_SERVICE_ACCOUNT);
const payLive = env => String(env.PAYPAL_ENV || '').trim().toLowerCase() === 'live';
const payCur = env => (String(env.PAY_CURRENCY || 'USD').trim().toUpperCase().replace(/[^A-Z]/g, '') || 'USD').slice(0, 3);
const payRate = env => payCur(env) === 'INR' ? 1 : (+env.INR_RATE > 0 ? +env.INR_RATE : 95);
const ppBase = env => payLive(env) ? 'https://api-m.paypal.com' : 'https://api-m.sandbox.paypal.com';
const NO_DECIMALS = ['JPY', 'HUF', 'TWD'];
function payValue(env, inr) {
  const cur = payCur(env), v = inr / payRate(env);
  return NO_DECIMALS.includes(cur) ? String(Math.max(1, Math.round(v))) : (Math.max(1, Math.round(v * 100)) / 100).toFixed(2);
}
let ppTok = { v: '', exp: 0, key: '' };
async function paypalToken(env) {
  const id = String(env.PAYPAL_CLIENT_ID).trim(), key = id + (payLive(env) ? ':live' : ':sandbox');
  if (ppTok.v && ppTok.key === key && ppTok.exp > Date.now() + 60e3) return ppTok.v;
  const r = await fetch(ppBase(env) + '/v1/oauth2/token', { method: 'POST',
    headers: { authorization: 'Basic ' + btoa(id + ':' + String(env.PAYPAL_CLIENT_SECRET).trim()), 'content-type': 'application/x-www-form-urlencoded' },
    body: 'grant_type=client_credentials', signal: ppWait() });
  const j = await r.json().catch(() => ({}));
  if (!j.access_token) throw new Error('PayPal sign-in failed. Check PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET' + (payLive(env) ? '' : ' (use the Sandbox keys)') + ': ' + (j.error_description || j.error || r.status));
  ppTok = { v: j.access_token, exp: Date.now() + (+j.expires_in || 3000) * 1000, key };
  return ppTok.v;
}
async function ppCall(env, method, path, body, requestId) {
  const headers = { authorization: 'Bearer ' + await paypalToken(env), 'content-type': 'application/json', prefer: 'return=representation' };
  if (requestId) headers['PayPal-Request-Id'] = requestId;
  const r = await fetch(ppBase(env) + path, { method, headers, body: body ? JSON.stringify(body) : undefined, signal: ppWait() });
  return { ok: r.ok, status: r.status, j: await r.json().catch(() => ({})) };
}
// PayPal sometimes answers very slowly: give up after 20 seconds so the app can say "try again"
const ppWait = () => (typeof AbortSignal !== 'undefined' && AbortSignal.timeout ? AbortSignal.timeout(20000) : undefined);
const ppIssue = j => String((j && j.details && j.details[0] && j.details[0].issue) || (j && j.name) || '');
const ppText = j => String((j && j.details && j.details[0] && (j.details[0].description || j.details[0].issue)) || (j && (j.message || j.name)) || '').slice(0, 200);
function toValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === 'boolean') return { booleanValue: v };
  if (typeof v === 'number') return Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v };
  if (typeof v === 'string') return { stringValue: v };
  if (Array.isArray(v)) return { arrayValue: { values: v.map(toValue) } };
  return { mapValue: { fields: toFields(v) } };
}
const toFields = o => { const f = {}; for (const k of Object.keys(o)) f[k] = toValue(o[k]); return f; };
async function fsPatch(pid, tok, path, obj) {
  const mask = Object.keys(obj).map(k => 'updateMask.fieldPaths=' + encodeURIComponent(k)).join('&');
  const r = await fetch(FS(pid) + path + '?' + mask + '&currentDocument.exists=true', { method: 'PATCH',
    headers: { authorization: 'Bearer ' + tok, 'content-type': 'application/json' }, body: JSON.stringify({ fields: toFields(obj) }) });
  if (!r.ok) throw new Error('Firestore write ' + r.status);
}
const rupees = x => Math.round((Number(x) || 0) * 100) / 100;
// what the patient owes — always read from the database, never from the phone
async function payItem(pid, tok, kind, id, me) {
  if (kind === 'fee') {
    const r = await fsGet(pid, tok, 'requests/' + id);
    if (!r || r.patientId !== me) return { err: 'This is not your consultation', code: 403 };
    if (!['accepted', 'waiting', 'live', 'completed'].includes(r.status)) return { err: 'You can pay after the doctor accepts your request', code: 409 };
    const d = await fsGet(pid, tok, 'public/' + safeId(r.doctorId));
    const inr = rupees(d && d.doc && d.doc.fee);
    if (!(inr > 0)) return { err: 'This doctor has not set a fee', code: 409 };
    return { doc: r, inr, path: 'requests/' + id, desc: 'Healvio consultation fee' + (d && d.name ? ' - ' + d.name : '') };
  }
  if (kind === 'order') {
    const o = await fsGet(pid, tok, 'orders/' + id);
    if (!o || o.patientId !== me) return { err: 'This is not your order', code: 403 };
    if (!['ready', 'partial'].includes(o.status)) return { err: 'You can pay after the store confirms your medicines', code: 409 };
    const inr = rupees(o.total);
    if (!(inr > 0)) return { err: 'The store has not added the price yet', code: 409 };
    return { doc: o, inr, path: 'orders/' + id, desc: 'Healvio medicines' + (o.storeName ? ' - ' + o.storeName : '') };
  }
  return { err: 'Unknown payment', code: 400 };
}
async function handlePay(step, request, env, reply) {
  const s = serviceAccount(env), pid = s.project_id;
  const tokP = googleToken(s); tokP.catch(() => {});
  let me, body;
  try { [me, body] = await Promise.all([verifyIdToken((request.headers.get('authorization') || '').replace(/^Bearer\s+/i, ''), pid), request.json().catch(() => null)]); }
  catch (e) { return reply({ error: 'Please sign in again' }, 401); }
  const kind = body && body.kind, id = safeId(body && body.id);
  if (!id || !['fee', 'order'].includes(kind)) return reply({ error: 'Bad request' }, 400);
  const tok = await tokP;
  const it = await payItem(pid, tok, kind, id, me);
  if (it.err) return reply({ error: it.err }, it.code);
  if (it.doc.paid) return reply({ ok: true, already: true, paid: it.doc.paid });
  const cur = payCur(env), value = payValue(env, it.inr), ref = kind + ':' + id;

  if (step === 'create') {
    const ctx = { brand_name: 'Healvio', shipping_preference: 'NO_SHIPPING', user_action: 'PAY_NOW' };
    // "go to PayPal and come back": the payer goes to PayPal's own page and PayPal brings them back to Healvio.
    // Works inside the installed app, where PayPal's pop-up window can get stuck. Only back to the site that asked.
    let back = '';
    if (body.redirect) {
      try {
        const u = new URL(String(body.back || '')), origin = request.headers.get('origin') || '';
        if (origin && u.origin === origin && (u.protocol === 'https:' || /^(localhost|127\.0\.0\.1)$/.test(u.hostname))) back = u.origin + u.pathname;
      } catch (e) {}
      if (!back) return reply({ error: 'Bad request' }, 400);
      const q = 'pk=' + encodeURIComponent(kind) + '&pi=' + encodeURIComponent(id);
      ctx.return_url = back + '?paypal=ok&' + q;
      ctx.cancel_url = back + '?paypal=cancel&' + q;
    }
    const o = await ppCall(env, 'POST', '/v2/checkout/orders', {
      intent: 'CAPTURE',
      purchase_units: [{ reference_id: ref, custom_id: (ref + ':' + me).slice(0, 127), description: it.desc.slice(0, 127),
        amount: { currency_code: cur, value } }],
      application_context: ctx
    });
    if (!o.ok || !o.j.id) return reply({ error: 'PayPal could not start the payment', detail: ppText(o.j) }, 502);
    const link = ((o.j.links || []).find(l => l && (l.rel === 'approve' || l.rel === 'payer-action')) || {}).href || '';
    const approve = back && /^https:\/\/www\.(sandbox\.)?paypal\.com\//.test(link) ? link : '';
    if (back && !approve) return reply({ error: 'PayPal could not start the payment', detail: 'no approval link' }, 502);
    return reply({ orderID: o.j.id, value, currency: cur, inr: it.inr, ...(approve ? { approve } : {}) });
  }

  // capture
  const oid = String((body && body.orderID) || '').replace(/[^\w-]/g, '').slice(0, 64);
  if (!oid) return reply({ error: 'Bad request' }, 400);
  let c = await ppCall(env, 'POST', '/v2/checkout/orders/' + oid + '/capture', null, 'healvio-cap-' + oid);
  if (!c.ok && c.status === 422 && ppIssue(c.j) === 'ORDER_ALREADY_CAPTURED') c = await ppCall(env, 'GET', '/v2/checkout/orders/' + oid);
  if (!c.ok) {
    const issue = ppIssue(c.j);
    if (issue === 'INSTRUMENT_DECLINED' || issue === 'PAYER_ACTION_REQUIRED') return reply({ error: 'Your payment method was declined. Please choose another.', retry: true }, 402);
    return reply({ error: 'PayPal could not finish the payment', detail: ppText(c.j) }, 502);
  }
  const pu = ((c.j.purchase_units || [])[0]) || {};
  const cap = (((pu.payments || {}).captures) || []).find(x => x && x.status === 'COMPLETED') || (((pu.payments || {}).captures) || [])[0] || {};
  const amt = cap.amount || pu.amount || {};
  if (pu.reference_id !== ref) return reply({ error: 'This PayPal payment is for something else' }, 409);
  if (c.j.status !== 'COMPLETED' || cap.status !== 'COMPLETED') return reply({ error: cap.status === 'PENDING' ? 'PayPal is still checking this payment. It will show as paid once PayPal completes it.' : 'The payment was not completed', status: cap.status || c.j.status || '' }, 409);
  if (amt.currency_code !== cur || Number(amt.value) + 1e-9 < Number(value)) return reply({ error: 'The amount paid does not match the price. Contact Healvio support.' }, 409);
  const paid = { by: 'paypal', orderId: oid, captureId: String(cap.id || ''), amount: String(amt.value), currency: amt.currency_code, inr: it.inr, at: Date.now(), test: !payLive(env) };
  await fsPatch(pid, tok, it.path, { paid, updatedAt: Date.now() });
  return reply({ ok: true, paid });
}

/* ================= PayPal refunds ================= */
async function handleRefund(request, env, reply) {
  const s = serviceAccount(env), pid = s.project_id;
  const tokP = googleToken(s); tokP.catch(() => {});
  let me, body;
  try { [me, body] = await Promise.all([verifyIdToken((request.headers.get('authorization') || '').replace(/^Bearer\s+/i, ''), pid), request.json().catch(() => null)]); }
  catch (e) { return reply({ error: 'Please sign in again' }, 401); }
  const kind = body && body.kind, id = safeId(body && body.id), reason = String((body && body.reason) || '').trim().slice(0, 200);
  if (!id || !['fee', 'order'].includes(kind)) return reply({ error: 'Bad request' }, 400);
  const tok = await tokP, path = (kind === 'fee' ? 'requests/' : 'orders/') + id;
  const [doc, adm] = await Promise.all([fsGet(pid, tok, path), fsGet(pid, tok, 'admins/' + safeId(me)).catch(() => null)]);
  if (!doc) return reply({ error: 'Not found' }, 404);
  const owner = kind === 'fee' ? doc.doctorId : doc.storeId;
  const who = doc.patientId === me ? 'patient' : owner === me ? (kind === 'fee' ? 'doctor' : 'store') : adm ? 'admin' : '';
  if (!who) return reply({ error: 'You cannot refund this' }, 403);
  if (!doc.paid || !doc.paid.captureId) return reply({ error: 'This was not paid with PayPal' }, 409);
  if (doc.refund) return reply({ ok: true, already: true, refund: doc.refund, status: doc.status });
  const before = kind === 'fee' ? ['requested', 'waiting', 'accepted'] : ['sent', 'ready', 'partial'];
  if (who === 'patient' && !before.includes(doc.status))
    return reply({ error: kind === 'fee' ? 'The consultation has already started, so it cannot be cancelled here. Please ask the doctor or Healvio support.' : 'Your medicines are already on the way or collected. Please contact the store.' }, 409);
  const capId = String(doc.paid.captureId).replace(/[^\w-]/g, '').slice(0, 64);
  const note = (reason || (kind === 'fee' ? 'Healvio consultation cancelled' : 'Healvio medicine order cancelled')).slice(0, 255);
  let r = await ppCall(env, 'POST', '/v2/payments/captures/' + capId + '/refund', { note_to_payer: note }, 'healvio-ref-' + capId);
  if (!r.ok && ppIssue(r.j) === 'CAPTURE_FULLY_REFUNDED') r = { ok: true, j: { id: '', status: 'COMPLETED' } };
  if (!r.ok) return reply({ error: 'PayPal could not refund this payment', detail: ppText(r.j) }, 502);
  const amt = (r.j && r.j.amount) || {};
  const refund = { id: String(r.j.id || ''), status: String(r.j.status || 'COMPLETED'), amount: String(amt.value || doc.paid.amount || ''), currency: String(amt.currency_code || doc.paid.currency || ''), inr: Number(doc.paid.inr) || 0, at: Date.now(), by: who, reason };
  const patch = { refund, updatedAt: Date.now() };
  const open = kind === 'fee' ? before : before.concat(['out']);
  if (body.cancel !== false && open.includes(doc.status)) {
    if (kind === 'fee') { if (who === 'patient') patch.status = 'cancelled'; else { patch.status = 'rejected'; patch.rejectReason = reason || 'Cancelled by the doctor'; } }
    else patch.status = who === 'patient' ? 'cancelled' : 'unavailable';
    patch.closedAt = Date.now();
  }
  await fsPatch(pid, tok, path, patch);
  return reply({ ok: true, refund, status: patch.status || doc.status });
}

/* ================= read a paper prescription photo (Workers AI, free) ================= */
function jsonIn(text) {
  const t = String(text || ''), a = t.indexOf('{'), b = t.lastIndexOf('}');
  if (a < 0 || b <= a) return null;
  try { return JSON.parse(t.slice(a, b + 1)); } catch (e) { return null; }
}
const RX_PROMPT = 'This is a photo of a doctor\'s prescription from India. Read only what is written on it; never add medicines. ' +
  'List every medicine with its strength/dose, timing (for example 1-0-1, OD, BD, TDS, at night), number of days and instructions (for example after food). ' +
  'If a word is hard to read, give your best reading and add " (check)" to it. ' +
  'Reply with JSON only: {"medicines":[{"name":"","dose":"","freq":"","days":"","note":""}],"doctor":"","date":"","readable":true}. ' +
  'If this is not a prescription or nothing can be read, reply {"medicines":[],"readable":false}.';
async function handleReadRx(request, env, reply) {
  if (env.FIREBASE_SERVICE_ACCOUNT) {
    try { await verifyIdToken((request.headers.get('authorization') || '').replace(/^Bearer\s+/i, ''), serviceAccount(env).project_id); }
    catch (e) { return reply({ error: 'Not signed in' }, 401); }
  }
  const body = await request.json().catch(() => null);
  const img = String((body && body.image) || '');
  const m = /^data:image\/(jpeg|jpg|png|webp);base64,([A-Za-z0-9+/=]+)$/.exec(img);
  if (!m || img.length > 2000000) return reply({ error: 'Please send a clear photo (JPEG or PNG, under 1.5 MB).' }, 400);
  const tries = [
    () => env.AI.run('@cf/meta/llama-4-scout-17b-16e-instruct', { messages: [{ role: 'user', content: [{ type: 'text', text: RX_PROMPT }, { type: 'image_url', image_url: { url: img } }] }], max_tokens: 900, temperature: 0.1 }),
    async () => {
      const bin = atob(m[2]), bytes = new Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const run = () => env.AI.run('@cf/meta/llama-3.2-11b-vision-instruct', { prompt: RX_PROMPT, image: bytes, max_tokens: 900 });
      try { return await run(); }
      catch (e) { if (/agree|licen[cs]e/i.test(String((e && e.message) || e))) { await env.AI.run('@cf/meta/llama-3.2-11b-vision-instruct', { prompt: 'agree' }).catch(() => {}); return run(); } throw e; }
    }
  ];
  let last = null;
  for (const t of tries) {
    try {
      const j = jsonIn(pickText(await t()));
      if (j && Array.isArray(j.medicines)) {
        const meds = j.medicines.filter(x => x && String(x.name || '').trim()).slice(0, 30).map(x => ({
          name: String(x.name).trim().slice(0, 80), dose: String(x.dose || '').trim().slice(0, 40), freq: String(x.freq || '').trim().slice(0, 40),
          days: String(x.days || '').replace(/[^\d]/g, '').slice(0, 3), note: String(x.note || '').trim().slice(0, 60) }));
        return reply({ medicines: meds, readable: j.readable !== false && meds.length > 0, doctor: String(j.doctor || '').slice(0, 80), date: String(j.date || '').slice(0, 30) });
      }
      last = new Error('no medicine list in the answer');
    } catch (e) { if (isQuota(e)) return aiFail(e, reply); last = e; }
  }
  return reply({ error: "AI couldn't read this photo. Please type the medicine names.", detail: String((last && last.message) || last).slice(0, 200) }, 502);
}

/* ================= medicine reminders (Cron trigger) ================= */
const SLOTS = ['m', 'a', 'n'], SLOT_NAME = { m: 'Morning', a: 'Afternoon', n: 'Night' };
const NEVER = 9000000000000000;
const remAt = (ds, hhmm, tz) => { const [y, mo, d] = ds.split('-').map(Number), [h, mi] = String(hhmm).split(':').map(Number); return Date.UTC(y, mo - 1, d, h, mi) + (Number(tz) || 0) * 60000; };
const remDay = (ms, tz) => new Date(ms - (Number(tz) || 0) * 60000).toISOString().slice(0, 10);
const remAdd = (ds, n) => { const [y, mo, d] = ds.split('-').map(Number); return new Date(Date.UTC(y, mo - 1, d + n)).toISOString().slice(0, 10); };
const remActive = (it, k, ds) => (it.slots || []).includes(k) && (!it.until || ds <= it.until) && (!it.from || ds >= it.from);
function remNext(r, after) {
  const tz = Number(r.tz) || 0, d0 = remDay(after, tz);
  for (let i = 0; i < 62; i++) {
    const ds = remAdd(d0, i);
    const c = SLOTS.filter(k => r.times && /^\d{1,2}:\d{2}$/.test(r.times[k] || '') && (r.items || []).some(it => remActive(it, k, ds)))
      .map(k => ({ k, ds, at: remAt(ds, r.times[k], tz) })).filter(x => x.at > after).sort((a, b) => a.at - b.at);
    if (c.length) return c[0];
  }
  return null;
}
async function fsUpsert(pid, tok, path, obj) {
  const mask = Object.keys(obj).map(k => 'updateMask.fieldPaths=' + encodeURIComponent(k)).join('&');
  await fetch(FS(pid) + path + '?' + mask, { method: 'PATCH', headers: { authorization: 'Bearer ' + tok, 'content-type': 'application/json' }, body: JSON.stringify({ fields: toFields(obj) }) });
}
async function pushTo(pid, tok, uid, data, ttl) {
  const rec = await fsGet(pid, tok, 'pushTokens/' + safeId(uid)).catch(() => null);
  const tokens = rec && Array.isArray(rec.tokens) ? rec.tokens.filter(t => typeof t === 'string' && t).slice(-5) : [];
  const res = await Promise.all(tokens.map(t => fcmSend(pid, tok, t, data, ttl).catch(() => 'error')));
  const gone = tokens.filter((t, k) => res[k] === 'gone');
  if (gone.length) await fsSetTokens(pid, tok, safeId(uid), tokens.filter(t => !gone.includes(t)));
  return res.filter(x => x === 'ok').length;
}
// a relay with a fixed username and password (e.g. ExpressTURN's free plan)
function fixedTurn(env) {
  const user = String(env.TURN_USERNAME || '').trim(), pass = String(env.TURN_PASSWORD || '').trim();
  if (!user || !pass) return [];
  const raw = String(env.TURN_SERVER || 'relay1.expressturn.com').trim().replace(/^turns?:\/*/i, '').replace(/\?.*$/, '').replace(/\/+$/, '');
  const m = /^\[?([^\]]+?)\]?(?::(\d+))?$/.exec(raw);
  if (!m || !/^[a-z0-9.\-:]+$/i.test(m[1])) return [];
  const host = m[1], port = m[2] && m[2] !== '53' ? m[2] : '3478';
  return [{ urls: [`turn:${host}:${port}?transport=udp`, `turn:${host}:${port}?transport=tcp`, `turns:${host}:443?transport=tcp`], username: user, credential: pass }];
}

async function runReminders(env, nowMs) {
  if (!env.FIREBASE_SERVICE_ACCOUNT) return { skipped: true };
  const s = serviceAccount(env), pid = s.project_id, tok = await googleToken(s), now = nowMs || Date.now();
  const prevP = fsGet(pid, tok, 'system/cron').catch(() => null);
  const q = await fetch(FS(pid).replace(/\/$/, '') + ':runQuery', { method: 'POST', headers: { authorization: 'Bearer ' + tok, 'content-type': 'application/json' },
    body: JSON.stringify({ structuredQuery: { from: [{ collectionId: 'reminders' }], where: { fieldFilter: { field: { fieldPath: 'nextAt' }, op: 'LESS_THAN_OR_EQUAL', value: { integerValue: String(now + 60000) } } }, limit: 200 } }) });
  const rows = q.ok ? await q.json() : [];
  const docs = (Array.isArray(rows) ? rows : []).filter(x => x && x.document).map(x => ({ ...fromFields(x.document.fields), id: x.document.name.split('/').pop() }));
  let sent = 0;
  for (const r of docs) {
    try {
      const tz = Number(r.tz) || 0, due = Number(r.nextAt) || 0, ds = remDay(due, tz);
      const k = SLOTS.find(x => r.times && r.times[x] && remAt(ds, r.times[x], tz) === due);
      if (r.on !== false && k && now - due < 2 * 3600e3) {
        const meds = (r.items || []).filter(it => remActive(it, k, ds));
        const key = 'rem-' + safeId(r.id) + '-' + ds + '-' + k;
        if (meds.length && await fsCreateOnce(pid, tok, key, now)) {
          sent += await pushTo(pid, tok, r.uid, { kind: 'alert', tag: key, title: `💊 ${SLOT_NAME[k]} medicines`,
            body: (meds.map(x => [x.name, x.dose].filter(Boolean).join(' ') + (x.note ? ` (${x.note})` : '')).join(', ')).slice(0, 300) + '. Tap to mark them as taken.',
            url: './?go=pHome' }, 3 * 3600);
        }
      }
      const nx = r.on === false ? null : remNext(r, Math.max(now, due));
      await fsPatch(pid, tok, 'reminders/' + safeId(r.id), nx ? { nextAt: nx.at, sentAt: now } : { nextAt: NEVER, on: false, sentAt: now });
    } catch (e) {}
  }
  // consultations running over time: reminders to the doctor and a delay notice to the next patients
  let timers = 0;
  try { timers = await runConsultTimers(pid, tok, now); } catch (e) {}
  // medicine reminders run every minute; payment reminders every 5 minutes (keeps the free database limit)
  const prev = await prevP;
  let paySent = 0, payAt = Number(prev && prev.payAt) || 0;
  if (now - payAt >= 270000) { try { paySent = await runPayReminders(env, pid, tok, now); payAt = now; } catch (e) {} }
  await fsUpsert(pid, tok, 'system/cron', { at: now, gap: prev && prev.at ? now - Number(prev.at) : 0, due: docs.length, sent, paySent, payAt, timers }).catch(() => {});
  return { due: docs.length, sent, paySent, timers };
}
/* ================= consultation timer (runs every minute) =================
 * After the booked minutes the doctor gets "time is up", and 10 minutes later a stronger reminder.
 * The next patients of the day are told once that the doctor is about 10 minutes late.
 * A consultation never ends by itself. Each alert has a fixed id, so the doctor's phone
 * and this worker never send the same alert twice (whoever saves it first sends it). */
const GRACE_MIN = 10;
const lenOfReq = r => { const n = Number(r && r.slotLen); return n >= 5 && n <= 180 ? n : 15; };
const hm12 = hm => { const [h, m] = String(hm).split(':').map(Number); return ((h % 12) || 12) + ':' + String(m).padStart(2, '0') + (h < 12 ? ' AM' : ' PM'); };
const bookKey = r => String(r.slotDate || '').replace(/-/g, '') + String(r.slotTime || '').replace(':', '');
const tzOf = r => r && r.tz !== undefined && r.tz !== null && r.tz !== '' ? Number(r.tz) || 0 : -330; // India time when the phone did not say
const tupText = (k, len, pname) => k === 1
  ? `⏰ The ${len}-minute consultation time with ${pname} is over. You have ${GRACE_MIN} extra minutes — please start wrapping up.`
  : `⚠️ ${pname}'s consultation is now ${GRACE_MIN} minutes over time. Please finish and end it when you're done. It will not end by itself.`;
const delayText = (dr, to, booked) => `⏳ ${dr} is running about ${GRACE_MIN} minutes late. Your consultation is now expected at about ${hm12(to)} (booked for ${hm12(booked)}). We'll alert you when the doctor is ready.`;
async function fsQuery(pid, tok, col, field, op, value, limit) {
  const q = await fetch(FS(pid).replace(/\/$/, '') + ':runQuery', { method: 'POST', headers: { authorization: 'Bearer ' + tok, 'content-type': 'application/json' },
    body: JSON.stringify({ structuredQuery: { from: [{ collectionId: col }], where: { fieldFilter: { field: { fieldPath: field }, op, value: toValue(value) } }, limit: limit || 100 } }) });
  if (!q.ok) throw new Error('Firestore query ' + q.status);
  const rows = await q.json();
  return (Array.isArray(rows) ? rows : []).filter(x => x && x.document).map(x => ({ ...fromFields(x.document.fields), id: x.document.name.split('/').pop() }));
}
// saves the alert only if nobody saved it before, then rings the phone: 'sent', 'exists' (sent before) or 'error' (try next minute)
async function sendNoteOnce(pid, tok, n) {
  let r;
  try {
    r = await fetch(FS(pid) + 'notifications?documentId=' + encodeURIComponent(n.id), { method: 'POST',
      headers: { authorization: 'Bearer ' + tok, 'content-type': 'application/json' }, body: JSON.stringify({ fields: toFields(n) }) });
  } catch (e) { return 'error'; }
  if (r.status === 409) return 'exists';
  if (!r.ok) return 'error';
  if (await fsCreateOnce(pid, tok, 'n-' + safeId(n.id), n.at)) await pushTo(pid, tok, n.to, noteData(n), 86400).catch(() => 0);
  return 'sent';
}
// who waits after a consultation that runs over: today's next bookings until a free gap absorbs the delay
function delayPlan(live, list, t) {
  const ds = live.slotDate, tz = tzOf(live), end = (Number(live.startedAt) || 0) + lenOfReq(live) * 60000;
  const c = list.filter(x => x.id !== live.id && x.doctorId === live.doctorId && ['accepted', 'waiting'].includes(x.status) && x.slotDate === ds && /^\d{2}:\d{2}$/.test(x.slotTime || ''))
    .map(x => ({ r: x, at: remAt(ds, x.slotTime, tz) })).filter(x => x.at >= t - 2 * 3600e3).sort((a, b) => a.at - b.at);
  let cur = Math.max(end + GRACE_MIN * 60000, t);
  const out = [];
  for (const x of c) {
    if (x.at >= cur || out.length >= 20) break;
    const exp = Math.max(x.at + GRACE_MIN * 60000, cur), loc = new Date(exp - tz * 60000).toISOString();
    if (x.r.delayFor !== bookKey(x.r)) out.push({ r: x.r, to: loc.slice(0, 10) === ds ? loc.slice(11, 16) : '23:59' });
    cur = exp + lenOfReq(x.r) * 60000;
  }
  return out;
}
async function runConsultTimers(pid, tok, now) {
  const live = await fsQuery(pid, tok, 'requests', 'status', 'EQUAL', 'live', 100);
  let sent = 0;
  for (const r of live) {
    try {
      const st = Number(r.startedAt) || 0, len = lenOfReq(r), over = now - (st + len * 60000), tup = Number(r.tup) || 0;
      if (!st || !r.doctorId || over < 0 || over > 6 * 3600e3) continue; // not over yet, or left open for hours
      const pname = String((r.patient && r.patient.name) || 'the patient').slice(0, 80), ref = { view: 'room', id: r.id }, path = 'requests/' + safeId(r.id);
      if (tup < 1) {
        const x = await sendNoteOnce(pid, tok, { id: 'tup1-' + r.id, to: r.doctorId, from: 'system', title: 'Consultation time is up', kind: 'info', ref, text: tupText(1, len, pname), at: now, read: false });
        if (x === 'sent') sent++;
        if (x !== 'error') await fsPatch(pid, tok, path, { tup: 1 }).catch(() => {});
      }
      if (!r.dlyAt && /^\d{4}-\d{2}-\d{2}$/.test(r.slotDate || '')) {
        const plan = delayPlan(r, await fsQuery(pid, tok, 'requests', 'slotDate', 'EQUAL', r.slotDate, 300), now);
        let failed = false;
        if (plan.length) {
          const d = await fsGet(pid, tok, 'public/' + safeId(r.doctorId)).catch(() => null), nm = String((d && d.name) || 'Your doctor').slice(0, 80);
          const dr = /^dr\.?\s/i.test(nm) || nm === 'Your doctor' ? nm : 'Dr. ' + nm;
          for (const p of plan) {
            const n = { id: 'dly-' + p.r.id + '-' + bookKey(p.r), to: p.r.patientId, from: 'system', title: 'Consultation delayed', kind: 'info', ref: { view: 'consult', id: p.r.id }, text: delayText(dr, p.to, p.r.slotTime), at: now, read: false };
            const x = await sendNoteOnce(pid, tok, n);
            if (x === 'sent') { sent++; await fsPatch(pid, tok, 'requests/' + safeId(p.r.id), { delayMin: GRACE_MIN, delayAt: now, delayTo: p.to, delayFor: bookKey(p.r), delayBy: r.id }).catch(() => {}); }
            if (x === 'error') failed = true;
          }
        }
        if (!failed) await fsPatch(pid, tok, path, { dlyAt: now }).catch(() => {});
      }
      if (over >= GRACE_MIN * 60000 && tup < 2) {
        const x = await sendNoteOnce(pid, tok, { id: 'tup2-' + r.id, to: r.doctorId, from: 'system', title: 'Extra time is over', kind: 'urgent', ref, text: tupText(2, len, pname), at: now, read: false });
        if (x === 'sent') sent++;
        if (x !== 'error') await fsPatch(pid, tok, path, { tup: 2 }).catch(() => {});
      }
    } catch (e) {}
  }
  return sent;
}
// "Pay before your consultation": one alert 60 minutes before the slot and one 10 minutes before
async function runPayReminders(env, pid, tok, now) {
  if (!payOn(env)) return 0;
  const q = await fetch(FS(pid).replace(/\/$/, '') + ':runQuery', { method: 'POST', headers: { authorization: 'Bearer ' + tok, 'content-type': 'application/json' },
    body: JSON.stringify({ structuredQuery: { from: [{ collectionId: 'requests' }], where: { fieldFilter: { field: { fieldPath: 'status' }, op: 'IN', value: { arrayValue: { values: [{ stringValue: 'accepted' }, { stringValue: 'waiting' }] } } } }, limit: 300 } }) });
  const rows = q.ok ? await q.json() : [];
  const list = (Array.isArray(rows) ? rows : []).filter(x => x && x.document).map(x => ({ ...fromFields(x.document.fields), id: x.document.name.split('/').pop() }));
  const fees = {};
  let sent = 0;
  for (const r of list) {
    try {
      if (r.paid || r.feeWaived || !r.patientId || !/^\d{4}-\d{2}-\d{2}$/.test(r.slotDate || '') || !/^\d{1,2}:\d{2}$/.test(r.slotTime || '')) continue;
      const tz = r.tz === undefined || r.tz === null ? -330 : Number(r.tz) || 0; // India time when the phone did not say
      const at = remAt(r.slotDate, r.slotTime, tz), mins = (at - now) / 60000;
      const step = mins <= 12 && mins > -20 ? 10 : mins <= 62 && mins > 12 ? 60 : 0;
      if (!step) continue;
      if (!(r.doctorId in fees)) { const d = await fsGet(pid, tok, 'public/' + safeId(r.doctorId)).catch(() => null); fees[r.doctorId] = { inr: rupees(d && d.doc && d.doc.fee), name: (d && d.name) || 'your doctor' }; }
      const f = fees[r.doctorId];
      if (!(f.inr > 0)) continue;
      if (!(await fsCreateOnce(pid, tok, 'pay-' + safeId(r.id) + '-' + step, now))) continue;
      const hh = String(r.slotTime).split(':').map(Number), t12 = ((hh[0] % 12) || 12) + ':' + String(hh[1]).padStart(2, '0') + (hh[0] < 12 ? ' AM' : ' PM');
      const name = /^dr\.?\s/i.test(f.name) ? f.name : 'Dr. ' + f.name;
      sent += await pushTo(pid, tok, r.patientId, { kind: 'urgent', tag: 'pay-' + safeId(r.id), url: './?go=consult&id=' + encodeURIComponent(safeId(r.id)),
        title: '🔔 Healvio · Pay to confirm your consultation',
        body: (step === 10 ? 'Your consultation with ' + name + ' is at ' + t12 + '. ' : 'Your consultation with ' + name + ' is today at ' + t12 + '. ') + 'Please pay the ₹' + f.inr + ' fee in Healvio so the doctor can start on time.' }, 3600);
    } catch (e) {}
  }
  return sent;
}
