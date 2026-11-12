// /push: clear reasons, a busy database does not block alerts, dead phone addresses removed
import fs from 'fs';
const SRC = process.env.WSRC || '../healvio-app/ai-server/worker.js';
fs.writeFileSync('./worker9.mjs', fs.readFileSync(SRC, 'utf8') + '\nexport { runReminders };\n');
const W = await import('./worker9.mjs');
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

db.set('pushTokens/pat', { id: 'pat', tokens: ['good1'] });
let r = await push('doc', { id: note('doc', 'pat'), to: 'pat' });
ok('normal alert: sent 1, phones 1', r.sent === 1 && r.phones === 1 && !r.fcm, r);

r = await push('doc', { id: note('doc', 'nobody'), to: 'nobody' });
ok('person without notifications: sent 0, phones 0 (clear reason)', r.sent === 0 && r.phones === 0, r);

db.set('pushTokens/pat2', { id: 'pat2', tokens: ['dead', 'good2'] });
r = await push('doc', { id: note('doc', 'pat2'), to: 'pat2' });
ok('dead address: other phone still gets it, dead one removed', r.sent === 1 && r.gone === 1 && JSON.stringify(db.get('pushTokens/pat2').tokens) === '["good2"]', r);

db.set('pushTokens/pat3', { id: 'pat3', tokens: ['dead'] });
r = await push('doc', { id: note('doc', 'pat3'), to: 'pat3' });
ok('only a dead address: says gone, list emptied', r.sent === 0 && r.gone === 1 && db.get('pushTokens/pat3').tokens.length === 0, r);

mode = { fcm403: true };
r = await push('doc', { id: note('doc', 'pat'), to: 'pat' });
ok("Google refuses: Google's exact reason is returned", r.sent === 0 && r.phones === 1 && /403/.test(r.fcm) && /PERMISSION_DENIED/.test(r.fcm) && /has not been used/.test(r.fcm), r);
mode = {};

db.set('pushTokens/pat4', { id: 'pat4', tokens: ['mismatch'] });
r = await push('doc', { id: note('doc', 'pat4'), to: 'pat4' });
ok('sender mismatch reported by its code', r.sent === 0 && /SENDER_ID_MISMATCH/.test(r.fcm), r);

const before = fcm.length, idW = note('doc', 'pat');
mode = { writeFail: true };
r = await push('doc', { id: idW, to: 'pat' });
ok('database write limit: the alert still goes out (was blocked before)', r.sent === 1 && fcm.length === before + 1, r);
mode = {};

const idT = note('doc', 'pat');
r = await push('doc', { id: idT, to: 'pat' });
const r2 = await push('doc', { id: idT, to: 'pat' });
ok('same alert twice: sent once only', r.sent === 1 && r2.skipped === 'already sent', [r, r2]);

mode = { readFail: true };
const t0 = Date.now();
r = await push('doc', { id: note('doc', 'pat'), to: 'pat' });
ok('database free limit: says free_limit quickly (no 4 s wait)', r.error === 'free_limit' && Date.now() - t0 < 1500, [r, Date.now() - t0]);
mode = {};

r = await push('doc', { id: 'missing-one', to: 'pat' });
ok('alert not in database: skipped with reason', r.sent === 0 && r.skipped === 'not a recent alert of yours', r);

r = await push('eve', { id: note('doc', 'pat'), to: 'pat' });
ok("someone else's alert cannot be sent", r.sent === 0 && /not a recent alert/.test(r.skipped || ''), r);

// Google sign-in failure (key switched off): clear reason
const W2src = fs.readFileSync(SRC, 'utf8');
fs.writeFileSync('./worker9b.mjs', W2src);
const Wb = (await import('./worker9b.mjs')).default;
mode = { login: true };
const rb = await (await Wb.fetch(new Request('https://w.test/push', { method: 'POST', headers: { origin: 'https://healvio.web.app', authorization: 'Bearer ' + await idToken('doc'), 'content-type': 'application/json' }, body: JSON.stringify({ id: note('doc', 'pat'), to: 'pat' }) }), ENV, { waitUntil() {} })).json();
ok('service account key wrong/switched off: google_login with Google\'s words', rb.error === 'google_login' && /Invalid JWT Signature/.test(rb.detail || ''), rb);
mode = {};

// reminders stay strict: when the database can't record them they are not sent again and again
db.set('reminders/rm1', { id: 'rm1', uid: 'pat', on: true, tz: -330, times: { m: '08:00' }, items: [{ name: 'Paracetamol', slots: ['m'] }], nextAt: Date.now() - 60000 });
mode = { writeFail: true };
const f0 = fcm.length;
await W.runReminders(ENV, Date.now());
ok('timed reminders are not sent when they cannot be recorded (no repeats)', fcm.length === f0, fcm.length - f0);
mode = {};

console.log('\n' + results.filter(Boolean).length + '/' + results.length + ' passed');
