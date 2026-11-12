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

const aiCalls = [];
let quota = false, badArgs = false, deadModel = '';
const AI = { run: async (model, input) => {
  aiCalls.push({ model, input });
  if (quota) throw new Error('3036: You have used up your daily free allocation of 10,000 neurons.');
  if (model === deadModel) throw new Error('5007: No such model');
  if (model.includes('whisper')) {
    if (badArgs && Object.keys(input).length > 1) throw new Error('5006: Error: oneOf at /vad_filter');
    return { text: input.audio.startsWith('SILENT') ? ' Thank you. ' : 'I have had fever since three days and body pain.' };
  }
  return { response: '{"summary":"Fever for 3 days.","key_points":["Rest"]}' };
} };
const env = { ALLOWED_ORIGINS: 'https://healvio.web.app', FIREBASE_SERVICE_ACCOUNT: SA, AI };
const req = async (path, body, tok, method = 'POST', e = env) => { const r = await worker.fetch(new Request('https://w.dev' + path, { method, headers: { Origin: 'https://healvio.web.app', 'content-type': 'application/json', ...(tok ? { authorization: 'Bearer ' + tok } : {}) }, body: method === 'POST' ? JSON.stringify(body) : undefined }), e); return [r.status, await r.json()]; };
let pass = 0, total = 0;
const ok = (n, c, x = '') => { total++; if (c) pass++; console.log((c ? 'PASS ' : 'FAIL ') + n, x === '' ? '' : '| ' + JSON.stringify(x).slice(0, 220)); };
const tPat = await idToken('pat1'), tDoc = await idToken('doc1'), tX = await idToken('stranger');
let r = await req('/status', null, null, 'GET'); ok('status: free AI + call notes available', r[1].ai === true && r[1].listen === true && r[1].push === true, r[1]);
r = await req('/status', null, null, 'GET', { ALLOWED_ORIGINS: 'https://healvio.web.app' }); ok('status: no AI until the binding is added', r[1].ai === false && r[1].listen === false, r[1]);
r = await req('/', { prompt: 'Summarize this consultation', tier: 'default' }, tPat);
ok('summary works on the free AI (no Claude key)', r[0] === 200 && r[1].text.includes('Fever for 3 days') && aiCalls[0].model === '@cf/meta/llama-3.3-70b-instruct-fp8-fast', [r, aiCalls[0] && aiCalls[0].model]);
ok('the AI is told to stay to the facts', aiCalls[0].input.messages[0].role === 'system' && /Never invent medical facts/.test(aiCalls[0].input.messages[0].content));
r = await req('/', { prompt: 'Translate', tier: 'quick' }, tPat); ok('translate uses the quick model', aiCalls[aiCalls.length - 1].model === '@cf/meta/llama-3.1-8b-instruct-fp8');
deadModel = '@cf/meta/llama-3.3-70b-instruct-fp8-fast'; r = await req('/', { prompt: 'Summ' }, tPat); deadModel = '';
ok('if a model is retired, the next one answers', r[0] === 200 && r[1].model === '@cf/meta/llama-4-scout-17b-16e-instruct', r[1]);
r = await req('/', { prompt: 'x' }, ''); ok('AI needs a signed-in Healvio user', r[0] === 401, r);
quota = true; r = await req('/', { prompt: 'x' }, tPat); quota = false; ok('free daily limit used up: clear message code', r[0] === 429 && r[1].error === 'free_limit', r);
// call notes
db.set('requests/rL', { id: 'rL', patientId: 'pat1', doctorId: 'doc1', status: 'live' });
db.set('requests/rDone', { id: 'rDone', patientId: 'pat1', doctorId: 'doc1', status: 'completed' });
const audio = 'UklGR' + 'A'.repeat(5000);
r = await req('/listen', { rid: 'rL', audio }, tPat); const wc = aiCalls[aiCalls.length - 1];
ok('call notes: speech becomes text', r[0] === 200 && r[1].text === 'I have had fever since three days and body pain.' && wc.model === '@cf/openai/whisper-large-v3-turbo' && wc.input.audio === audio, r);
r = await req('/listen', { rid: 'rL', audio }, tDoc); ok('doctor side works too', r[0] === 200 && !!r[1].text);
r = await req('/listen', { rid: 'rL', audio }, tX); ok('strangers cannot use call notes', r[0] === 403, r);
r = await req('/listen', { rid: 'rDone', audio }, tPat); ok('only during a live consultation', r[0] === 403, r);
r = await req('/listen', { rid: 'rL', audio: 'SILENT' + 'A'.repeat(5000) }, tPat); ok('silence ("Thank you.") is dropped', r[0] === 200 && r[1].text === '', r);
badArgs = true; r = await req('/listen', { rid: 'rL', audio }, tPat); badArgs = false; ok('works even if extra options are refused', r[0] === 200 && !!r[1].text, r);
r = await req('/listen', { rid: 'rL', audio: 'abc' }, tPat); ok('rejects broken audio', r[0] === 400, r);
quota = true; r = await req('/listen', { rid: 'rL', audio }, tPat); quota = false; ok('call notes: daily limit message', r[0] === 429 && r[1].error === 'free_limit', r);
r = await req('/listen', { rid: 'rL', audio }, tPat, 'POST', { ...env, AI: undefined }); ok('clear message when the AI binding is missing', r[0] === 500 && /Workers AI binding/.test(r[1].error), r);
console.log(`PASSED ${pass} / ${total}`);
