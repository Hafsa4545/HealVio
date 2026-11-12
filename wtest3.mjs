import worker from './worker.mjs';
const S = crypto.subtle, RSA = { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' };
const gen = () => S.generateKey({ ...RSA, modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]) }, true, ['sign', 'verify']);
const b64u = buf => Buffer.from(buf).toString('base64url');
const PID = 'healvio';
const idKeys = await gen(), saKeys = await gen(), evil = await gen();
const jwk = { ...(await S.exportKey('jwk', idKeys.publicKey)), kid: 'k1', alg: 'RS256', use: 'sig' };
const pem = '-----BEGIN PRIVATE KEY-----\n' + Buffer.from(await S.exportKey('pkcs8', saKeys.privateKey)).toString('base64').match(/.{1,64}/g).join('\n') + '\n-----END PRIVATE KEY-----\n';
const SA = JSON.stringify({ type: 'service_account', project_id: PID, private_key_id: 'pk1', private_key: pem, client_email: 'firebase-adminsdk@healvio.iam.gserviceaccount.com' });
async function idToken(uid, opts = {}) {
  const t = Math.floor(Date.now() / 1000);
  const h = b64u(JSON.stringify({ alg: 'RS256', kid: 'k1', typ: 'JWT' }));
  const p = b64u(JSON.stringify({ aud: opts.aud || PID, iss: 'https://securetoken.google.com/' + (opts.aud || PID), sub: uid, iat: t - 10, exp: t + 3600 }));
  return h + '.' + p + '.' + b64u(await S.sign(RSA, (opts.key || idKeys).privateKey, Buffer.from(h + '.' + p)));
}
// --- fake Google: Firestore, OAuth, FCM ---
const enc = v => typeof v === 'string' ? { stringValue: v } : typeof v === 'number' ? { integerValue: String(v) } : typeof v === 'boolean' ? { booleanValue: v } : Array.isArray(v) ? { arrayValue: { values: v.map(enc) } } : v && typeof v === 'object' ? { mapValue: { fields: Object.fromEntries(Object.entries(v).map(([k, x]) => [k, enc(x)])) } } : { nullValue: null };
const db = new Map(), sent = [], calls = { oauth: 0, jwks: 0 };
const FSB = `https://firestore.googleapis.com/v1/projects/${PID}/databases/(default)/documents/`;
globalThis.fetch = async (url, init = {}) => {
  url = String(url);
  if (url.startsWith('https://www.googleapis.com/service_accounts/v1/jwk/securetoken')) { calls.jwks++; return new Response(JSON.stringify({ keys: [jwk] }), { headers: { 'cache-control': 'public, max-age=20000' } }); }
  if (url === 'https://oauth2.googleapis.com/token') {
    calls.oauth++;
    const a = new URLSearchParams(init.body).get('assertion').split('.');
    const ok = await S.verify(RSA, saKeys.publicKey, Buffer.from(a[2], 'base64url'), Buffer.from(a[0] + '.' + a[1]));
    const c = JSON.parse(Buffer.from(a[1], 'base64url'));
    if (!ok || c.iss !== 'firebase-adminsdk@healvio.iam.gserviceaccount.com' || !/firebase\.messaging/.test(c.scope) || !/datastore/.test(c.scope)) return new Response(JSON.stringify({ error: 'invalid_grant' }), { status: 400 });
    return new Response(JSON.stringify({ access_token: 'gtok', expires_in: 3600 }));
  }
  if ((init.headers || {}).authorization !== 'Bearer gtok') return new Response('unauth', { status: 401 });
  if (url.startsWith('https://fcm.googleapis.com/v1/projects/' + PID + '/messages:send')) {
    const m = JSON.parse(init.body).message; sent.push(m);
    if (m.token === 'dead') return new Response(JSON.stringify({ error: { status: 'NOT_FOUND', details: [{ errorCode: 'UNREGISTERED' }] } }), { status: 404 });
    return new Response(JSON.stringify({ name: 'projects/x/messages/1' }));
  }
  if (url.startsWith(FSB)) {
    const u = new URL(url), path = decodeURIComponent(u.pathname.split('/documents/')[1]);
    if (path === 'pushLog' && init.method === 'POST') { const k = 'pushLog/' + u.searchParams.get('documentId'); if (db.has(k)) return new Response('{}', { status: 409 }); db.set(k, { at: 1 }); return new Response('{}'); }
    if (init.method === 'PATCH') { const f = JSON.parse(init.body).fields; const cur = db.get(path) || {}; cur.tokens = f.tokens.arrayValue.values.map(v => v.stringValue); db.set(path, cur); return new Response('{}'); }
    if (path === 'admins') return new Response(JSON.stringify({ documents: [...db.keys()].filter(k => k.startsWith('admins/')).map(k => ({ name: 'projects/healvio/databases/(default)/documents/' + k })) }));
    if (!db.has(path)) return new Response('{}', { status: 404 });
    return new Response(JSON.stringify({ name: path, fields: enc(db.get(path)).mapValue.fields, updateTime: '2026-11-10T00:00:00Z' }));
  }
  return new Response('?', { status: 500 });
};
const env = { ALLOWED_ORIGINS: 'https://healvio.web.app', FIREBASE_SERVICE_ACCOUNT: SA };
const post = async (body, tok, origin = 'https://healvio.web.app', e = env) => { const r = await worker.fetch(new Request('https://w.dev/push', { method: 'POST', headers: { Origin: origin, 'content-type': 'application/json', authorization: 'Bearer ' + tok }, body: JSON.stringify(body) }), e); return [r.status, await r.json()]; };
const now = Date.now(); let r, pass = 0, total = 0;
const ok = (n, c, x = '') => { total++; if (c) pass++; console.log((c ? 'PASS ' : 'FAIL ') + n, x === '' ? '' : '| ' + JSON.stringify(x)); };
db.set('notifications/n1', { id: 'n1', from: 'pat1', to: 'doc1', text: 'New consultation request from Ravi', at: now, ref: { view: 'consult', id: 'r1' }, kind: 'info', read: false });
db.set('pushTokens/doc1', { id: 'doc1', tokens: ['t-phone', 'dead'] });
const tPat = await idToken('pat1');
r = await post({ id: 'n1' }, tPat);
ok('alert delivered to the doctor\'s phone', r[0] === 200 && r[1].sent === 1, r);
const m = sent.find(x => x.token === 't-phone');
ok('message is data-only with text + deep link', m && m.data.body === 'New consultation request from Ravi' && m.data.url === './?go=consult&id=r1' && m.data.title === 'Healvio · Consultation', m && m.data);
ok('high urgency, kept 1 day', m && m.webpush.headers.Urgency === 'high' && m.webpush.headers.TTL === '86400');
ok('uninstalled phone removed from the list', JSON.stringify(db.get('pushTokens/doc1').tokens) === '["t-phone"]', db.get('pushTokens/doc1').tokens);
r = await post({ id: 'n1' }, tPat); ok('same alert never sent twice', r[1].sent === 0 && r[1].skipped === 'already sent', r);
db.set('notifications/n2', { id: 'n2', from: 'someoneelse', to: 'doc1', text: 'spam', at: now });
r = await post({ id: 'n2' }, tPat); ok('cannot push an alert someone else wrote', r[1].sent === 0, r);
db.set('notifications/n3', { id: 'n3', from: 'pat1', to: 'doc1', text: 'old', at: now - 3600e3 });
r = await post({ id: 'n3' }, tPat); ok('old alerts are not re-sent', r[1].sent === 0, r);
db.set('admins/a1', {}); db.set('admins/a2', {}); db.set('pushTokens/a1', { tokens: ['ta1'] }); db.set('pushTokens/a2', { tokens: ['ta2a', 'ta2b'] });
db.set('notifications/n4', { id: 'n4', from: 'pat1', to: 'admin', text: 'Request: Ravi → Dr. Ananya', at: now, kind: 'urgent', ref: { view: 'consult', id: 'r1' } });
r = await post({ id: 'n4' }, tPat); ok('admin alerts reach every admin phone', r[1].sent === 3, r);
ok('urgent alert title', /^🔔 Healvio · /.test(sent.find(x => x.token === 'ta1').data.title), sent.find(x => x.token === 'ta1').data.title);
db.set('calls/c1', { id: 'c1', rid: 'r1', from: 'pat1', to: 'doc1', fromName: 'Ravi Kumar', kind: 'video', status: 'ringing', createdAt: now });
r = await post({ call: 'c1' }, tPat);
const cm = sent[sent.length - 1];
ok('incoming call rings the doctor\'s phone', r[1].sent === 1 && cm.data.kind === 'call' && cm.data.title === '📹 Incoming video call' && cm.data.body === 'Ravi Kumar is calling you. Tap to answer.' && cm.data.url === './?go=room&id=r1', cm.data);
ok('call alert expires in 30 s', cm.webpush.headers.TTL === '30');
r = await post({ call: 'c1', n: 2 }, tPat); ok('call rings again (2nd ring)', r[1].sent === 1, r);
r = await post({ call: 'c1', n: 2 }, tPat); ok('same ring never sent twice', r[1].sent === 0, r);
db.set('calls/c1', { ...db.get('calls/c1'), status: 'cancelled' });
r = await post({ call: 'c1', n: 3 }, tPat); ok('stops ringing once cancelled', r[1].sent === 0, r);
r = await post({ callEnd: 'c1' }, tPat); const em = sent[sent.length - 1];
ok('ringing turns into Missed video call (same notification)', r[1].sent === 1 && em.data.kind === 'callend' && em.data.tag === 'call-c1' && em.data.title === '📹 Missed video call', em.data);
r = await post({ callEnd: 'c1' }, await idToken('doc1')); ok('only the caller can send missed call', r[1].sent === 0, r);
db.set('calls/c2', { id: 'c2', rid: 'r1', from: 'pat1', to: 'doc1', kind: 'audio', status: 'ended', createdAt: now });
r = await post({ call: 'c2' }, tPat); ok('ended call does not ring', r[1].sent === 0, r);
r = await post({ call: 'c1' }, await idToken('doc1')); ok('only the caller can ring', r[1].sent === 0, r);
r = await post({ id: 'n1' }, await idToken('pat1', { key: evil })); ok('fake sign-in rejected', r[0] === 401, r);
r = await post({ id: 'n1' }, await idToken('pat1', { aud: 'other-project' })); ok('token from another project rejected', r[0] === 401, r);
r = await post({ id: 'n1' }, ''); ok('no sign-in rejected', r[0] === 401, r);
r = await post({ id: 'n1' }, tPat, 'https://evil.example'); ok('other websites blocked', r[0] === 403, r);
r = await post({ id: 'n1' }, tPat, 'https://healvio.web.app', { ALLOWED_ORIGINS: 'https://healvio.web.app' }); ok('clear message when service account missing', r[0] === 500 && /FIREBASE_SERVICE_ACCOUNT/.test(r[1].error), r);
r = await post({ id: 'n1' }, tPat, 'https://healvio.web.app', { ...env, FIREBASE_SERVICE_ACCOUNT: '{not json' }); ok('clear message when service account is wrong', r[0] === 500 && /not the right JSON/.test(r[1].error), r);
const pf = await worker.fetch(new Request('https://w.dev/push', { method: 'OPTIONS', headers: { Origin: 'https://healvio.web.app' } }), env);
ok('browser preflight allows the sign-in header', pf.status === 204 && /authorization/.test(pf.headers.get('Access-Control-Allow-Headers')));
ok('Google keys and token are reused (fast)', calls.jwks <= 2 && calls.oauth === 1, calls);
console.log(`PASSED ${pass} / ${total}`);
