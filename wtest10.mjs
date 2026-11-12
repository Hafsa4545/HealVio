// /push: clear reasons, a busy database does not block alerts, dead phone addresses removed
import fs from 'fs';
const SRC = process.env.WSRC || '../healvio-app/ai-server/worker.js';
fs.writeFileSync('./worker10.mjs', fs.readFileSync(SRC, 'utf8') + '\nexport { runReminders };\n');
const W = await import('./worker10.mjs');
const worker = W.default;
const S = crypto.subtle, RSA = { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' };
const gen = () => S.generateKey({ ...RSA, modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]) }, true, ['sign', 'verify']);
const b64u = buf => Buffer.from(buf).toString('base64url');
const PID = 'healvio';
const idKeys = await gen(), saKeys = await gen();
const jwk = { ...(await S.exportKey('jwk', idKeys.publicKey)), kid: 'k1', alg: 'RS256', use: 'sig' };
const pem = '-----BEGIN PRIVATE KEY-----\n' + Buffer.from(await S.exportKey('pkcs8', saKeys.privateKey)).toString('base64').match(/.{1,64}/g).join('\n') + '\n-----END PRIVATE KEY-----\n';
const SA = JSON.stringify({ type: 'service_account', project_id: PID, private_key_id: 'pk1', private_key: pem, client_email: 'x@healvio.iam.gserviceaccount.com' });
async function idToken(uid) {
  const t = Math.floor(Date.now() / 1000);
  const h = b64u(JSON.stringify({ alg: 'RS256', kid: 'k1', typ: 'JWT' }));
  const p = b64u(JSON.stringify({ aud: PID, iss: 'https://securetoken.google.com/' + PID, sub: uid, iat: t - 10, exp: t + 3600 }));
  return h + '.' + p + '.' + b64u(await S.sign(RSA, idKeys.privateKey, Buffer.from(h + '.' + p)));
}
const enc = v => typeof v === 'string' ? { stringValue: v } : typeof v === 'number' ? { integerValue: String(v) } : typeof v === 'boolean' ? { booleanValue: v } : Array.isArray(v) ? { arrayValue: { values: v.map(enc) } } : v && typeof v === 'object' ? { mapValue: { fields: Object.fromEntries(Object.entries(v).map(([k, x]) => [k, enc(x)])) } } : { nullValue: null };
const dec = v => 'stringValue' in v ? v.stringValue : 'integerValue' in v ? Number(v.integerValue) : 'booleanValue' in v ? v.booleanValue : 'mapValue' in v ? Object.fromEntries(Object.entries(v.mapValue.fields || {}).map(([k, x]) => [k, dec(x)])) : 'arrayValue' in v ? (v.arrayValue.values || []).map(dec) : null;
const db = new Map(), fcm = [];
const FSB = `https://firestore.googleapis.com/v1/projects/${PID}/databases/(default)/documents`;
const J = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json' } });
let mode = {};
globalThis.fetch = async (url, init = {}) => {
  url = String(url); const h = init.headers || {};
  if (url.startsWith('https://www.googleapis.com/service_accounts/v1/jwk/securetoken')) return new Response(JSON.stringify({ keys: [jwk] }), { headers: { 'cache-control': 'public, max-age=20000' } });
  if (url.startsWith('https://api-m.sandbox.paypal.com/v1/oauth2/token')) return mode.pp ? J({ error: 'invalid_client', error_description: 'Client Authentication failed' }, 401) : J({ access_token: 'pp', expires_in: 3000 });
  if (url === 'https://oauth2.googleapis.com/token') return mode.login ? J({ error: 'invalid_grant', error_description: 'Invalid JWT Signature.' }, 400) : J({ access_token: 'gtok', expires_in: 3600 });
  if (url.startsWith('https://fcm.googleapis.com/')) {
    const m = JSON.parse(init.body).message; fcm.push(m);
    if (m.token === 'dead') return J({ error: { code: 404, status: 'NOT_FOUND', message: 'Requested entity was not found.', details: [{ errorCode: 'UNREGISTERED' }] } }, 404);
    if (mode.fcm403) return J({ error: { code: 403, status: 'PERMISSION_DENIED', message: 'Firebase Cloud Messaging API has not been used in project healvio before or it is disabled.' } }, 403);
    if (m.token === 'mismatch') return J({ error: { code: 403, status: 'PERMISSION_DENIED', message: 'SenderId mismatch', details: [{ errorCode: 'SENDER_ID_MISMATCH' }] } }, 403);
    return J({ name: 'm1' });
  }
  if (h.authorization !== 'Bearer gtok') return new Response('unauth', { status: 401 });
  if (url.startsWith(FSB + '/')) {
    const u = new URL(url), path = decodeURIComponent(u.pathname.split('/documents/')[1]);
    if (init.method === 'POST') { if (mode.writeFail) return J({ error: { code: 429, status: 'RESOURCE_EXHAUSTED' } }, 429); const key = path + '/' + u.searchParams.get('documentId'); if (db.has(key)) return J({}, 409); db.set(key, {}); return J({}); }
    if (init.method === 'PATCH') { const f = JSON.parse(init.body).fields, cur = db.get(path) || {}; for (const k of u.searchParams.getAll('updateMask.fieldPaths')) cur[k] = dec(f[k]); db.set(path, cur); return J({}); }
    if (mode.readFail) return J({ error: { code: 429, status: 'RESOURCE_EXHAUSTED', message: 'Quota exceeded.' } }, 429);
    if (!db.has(path)) return J({}, 404);
    return J({ name: path, fields: enc(db.get(path)).mapValue.fields });
  }
  return new Response('?', { status: 500 });
};
const results = []; const ok = (n, c, x) => { results.push(!!c); console.log((c ? 'PASS ' : 'FAIL ') + n + (x !== undefined ? ' | ' + JSON.stringify(x).slice(0, 300) : '')); };
const ENV = { FIREBASE_SERVICE_ACCOUNT: SA, ALLOWED_ORIGINS: 'https://healvio.web.app' };
const push = async (uid, body) => { const r = await worker.fetch(new Request('https://w.test/push', { method: 'POST', headers: { origin: 'https://healvio.web.app', authorization: 'Bearer ' + await idToken(uid), 'content-type': 'application/json' }, body: JSON.stringify(body) }), ENV, { waitUntil() {} }); return r.json(); };
let k = 0;
const note = (from, to) => { const id = 'n' + (++k); db.set('notifications/' + id, { id, from, to, text: 'Hello ' + id, at: Date.now(), kind: 'info', ref: { view: 'consult', id: 'r1' } }); return id; };


const AI = { async run(model) { if (mode.ai === 'quota') throw new Error('3036: You have used up your daily free allocation of 10,000 neurons'); return { response: 'OK' }; } };
const PENV = { ...ENV, AI, PAYPAL_CLIENT_ID: 'cid', PAYPAL_CLIENT_SECRET: 'sec' };
const status = async (q, uid, env, mod) => { const h = { origin: 'https://healvio.web.app' }; if (uid) h.authorization = 'Bearer ' + await idToken(uid); const r = await (mod || worker).fetch(new Request('https://w.test/status' + q, { headers: h }), env || PENV, { waitUntil() {} }); return r.json(); };
let s = await status('', null);
ok('plain status (every app start): no live check, no sign-in needed', s.push === true && !('check' in s), s);
s = await status('?check=1', null);
ok('live check needs a signed-in person', s.check && s.check.error === 'sign in', s.check);
s = await status('?check=1', 'adm');
ok('live check: all OK', JSON.stringify(s.check) === JSON.stringify({ google: 'ok', paypal: 'ok', ai: 'ok', db: 'ok' }) || (s.check.google === 'ok' && s.check.db === 'ok' && s.check.paypal === 'ok' && s.check.ai === 'ok'), s.check);
mode = { readFail: true };
s = await status('?check=1', 'adm');
ok('live check: database free limit', s.check.db === 'free_limit', s.check);
mode = { pp: true };
fs.writeFileSync('./worker10c.mjs', fs.readFileSync(SRC, 'utf8'));
const Wc = (await import('./worker10c.mjs')).default;
s = await status('?check=1', 'adm', PENV, Wc);
ok('live check: PayPal key wrong, with PayPal\'s words', /PayPal sign-in failed/.test(s.check.paypal) && /Client Authentication failed/.test(s.check.paypal) && s.check.google === 'ok', s.check);
mode = { ai: 'quota' };
s = await status('?check=1', 'adm');
ok('live check: AI free limit', s.check.ai === 'free_limit', s.check);
mode = { login: true };
fs.writeFileSync('./worker10d.mjs', fs.readFileSync(SRC, 'utf8'));
const Wd = (await import('./worker10d.mjs')).default;
s = await status('?check=1', 'adm', PENV, Wd);
ok('live check: Google key wrong, with Google\'s words; database not tried', /Invalid JWT Signature/.test(s.check.google) && !('db' in s.check), s.check);
mode = {};
s = await status('?check=1', 'adm', { ALLOWED_ORIGINS: 'https://healvio.web.app' });
ok('live check: nothing set → says missing', s.check.google === 'missing' && s.check.paypal === 'missing' && s.check.ai === 'missing', s.check);
s = await status('?check=1', 'adm', { ...PENV, FIREBASE_SERVICE_ACCOUNT: '{bad json' });
ok('live check: broken service account text → clear message', /not the right JSON/.test(s.check.google), s.check);
console.log('\n' + results.filter(Boolean).length + '/' + results.length + ' passed');
