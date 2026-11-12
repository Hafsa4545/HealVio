// refunds, paper prescription reading, medicine reminders
import fs from 'fs';
fs.writeFileSync('./worker6.mjs', fs.readFileSync('../healvio-app/ai-server/worker.js', 'utf8') + '\nexport { runReminders, remNext, remAt, remDay };\n');
const W = await import('./worker6.mjs');
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
const enc = v => typeof v === 'string' ? { stringValue: v } : typeof v === 'number' ? (Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v }) : typeof v === 'boolean' ? { booleanValue: v } : Array.isArray(v) ? { arrayValue: { values: v.map(enc) } } : v && typeof v === 'object' ? { mapValue: { fields: Object.fromEntries(Object.entries(v).map(([k, x]) => [k, enc(x)])) } } : { nullValue: null };
const dec = v => 'stringValue' in v ? v.stringValue : 'integerValue' in v ? Number(v.integerValue) : 'doubleValue' in v ? v.doubleValue : 'booleanValue' in v ? v.booleanValue : 'mapValue' in v ? Object.fromEntries(Object.entries(v.mapValue.fields || {}).map(([k, x]) => [k, dec(x)])) : 'arrayValue' in v ? (v.arrayValue.values || []).map(dec) : null;
const db = new Map(), log = [], fcm = [];
const FSB = `https://firestore.googleapis.com/v1/projects/${PID}/databases/(default)/documents`;
const PPB = 'https://api-m.sandbox.paypal.com';
let refundMode = 'ok';
const J = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json' } });
globalThis.fetch = async (url, init = {}) => {
  url = String(url); const h = init.headers || {};
  if (url.startsWith('https://www.googleapis.com/service_accounts/v1/jwk/securetoken')) return new Response(JSON.stringify({ keys: [jwk] }), { headers: { 'cache-control': 'public, max-age=20000' } });
  if (url === 'https://oauth2.googleapis.com/token') return J({ access_token: 'gtok', expires_in: 3600 });
  if (url.startsWith(PPB)) {
    const path = url.slice(PPB.length); log.push({ pp: init.method + ' ' + path, rid: h['PayPal-Request-Id'], body: init.body });
    if (path === '/v1/oauth2/token') return J({ access_token: 'pptok', expires_in: 32400 });
    const m = /^\/v2\/payments\/captures\/([\w-]+)\/refund$/.exec(path);
    if (m) {
      if (refundMode === 'full') return J({ name: 'UNPROCESSABLE_ENTITY', details: [{ issue: 'CAPTURE_FULLY_REFUNDED' }] }, 422);
      if (refundMode === 'fail') return J({ name: 'UNPROCESSABLE_ENTITY', details: [{ issue: 'REFUND_FAILED_INSUFFICIENT_FUNDS', description: 'Not enough money' }] }, 422);
      return J({ id: 'RF-' + m[1], status: 'COMPLETED', amount: { value: '3.16', currency_code: 'USD' } }, 201);
    }
    return J({}, 404);
  }
  if (url.startsWith('https://fcm.googleapis.com/')) { fcm.push(JSON.parse(init.body).message); return J({ name: 'm1' }); }
  if (h.authorization !== 'Bearer gtok') return new Response('unauth', { status: 401 });
  if (url === FSB + ':runQuery') {
    const q = JSON.parse(init.body).structuredQuery, lim = Number(q.where.fieldFilter.value.integerValue);
    const out = [...db.entries()].filter(([k, v]) => k.startsWith('reminders/') && Number(v.nextAt) <= lim).map(([k, v]) => ({ document: { name: FSB + '/' + k, fields: enc(v).mapValue.fields } }));
    return J(out.length ? out : [{ readTime: 'x' }]);
  }
  if (url.startsWith(FSB + '/')) {
    const u = new URL(url), path = decodeURIComponent(u.pathname.split('/documents/')[1]);
    if (init.method === 'POST' && path === 'pushLog') { const id = u.searchParams.get('documentId'); if (db.has('pushLog/' + id)) return J({}, 409); db.set('pushLog/' + id, {}); return J({}); }
    if (init.method === 'PATCH') {
      if (u.searchParams.get('currentDocument.exists') === 'true' && !db.has(path)) return J({}, 404);
      const f = JSON.parse(init.body).fields, cur = db.get(path) || {};
      for (const k of u.searchParams.getAll('updateMask.fieldPaths')) cur[k] = dec(f[k]);
      db.set(path, cur); log.push({ fsPatch: path, mask: u.searchParams.getAll('updateMask.fieldPaths') }); return J({});
    }
    if (!db.has(path)) return J({}, 404);
    return J({ name: path, fields: enc(db.get(path)).mapValue.fields });
  }
  return new Response('?', { status: 500 });
};
let aiMode = 'scout';
const aiCalls = [];
const AI = { async run(model, input) {
  aiCalls.push({ model, input });
  if (aiMode === 'quota') throw new Error('3036: you have used up your daily free allocation of 10,000 neurons');
  if (model.includes('llama-4-scout')) {
    if (aiMode === 'scout') return { response: 'Here you go:\n{"medicines":[{"name":"Augmentin 625","dose":"625 mg","freq":"1-0-1","days":"5 days","note":"after food"},{"name":"Pan 40","dose":"40 mg","freq":"1-0-0","days":"5","note":"before breakfast"},{"name":""}],"doctor":"Dr. Rao","readable":true}' };
    throw new Error('image input not supported');
  }
  if (model.includes('llama-3.2-11b-vision')) {
    if (input.prompt === 'agree') { this.agreed = true; return { response: 'ok' }; }
    if (!this.agreed) throw new Error('5016: Prior to using this model, you must submit the prompt agree');
    if (!Array.isArray(input.image) || typeof input.image[0] !== 'number') throw new Error('bad image');
    return { response: '{"medicines":[{"name":"Dolo 650","dose":"650 mg","freq":"SOS","days":"3","note":""}],"readable":true}' };
  }
  throw new Error('unknown model');
} };
const ENV = { ALLOWED_ORIGINS: 'https://healvio.web.app', FIREBASE_SERVICE_ACCOUNT: SA, PAYPAL_CLIENT_ID: 'CID', PAYPAL_CLIENT_SECRET: 'SECRET', AI };
const req = async (path, body, tok, e = ENV) => { const r = await worker.fetch(new Request('https://w.dev' + path, { method: 'POST', headers: { Origin: 'https://healvio.web.app', 'content-type': 'application/json', ...(tok ? { authorization: 'Bearer ' + tok } : {}) }, body: JSON.stringify(body) }), e); return [r.status, await r.json()]; };
let pass = 0, total = 0;
const ok = (n, c, x = '') => { total++; if (c) pass++; console.log((c ? 'PASS ' : 'FAIL ') + n, x === '' ? '' : '| ' + JSON.stringify(x).slice(0, 260)); };
const [tPat, tDoc, tSt, tAdm, tOther] = await Promise.all(['pat1', 'doc1', 'st1', 'adm1', 'x9'].map(idToken));
const paid = cap => ({ by: 'paypal', orderId: 'O-' + cap, captureId: cap, amount: '3.16', currency: 'USD', inr: 300, at: 1, test: true });
db.set('admins/adm1', { email: 'hmc' });
db.set('requests/rA', { id: 'rA', patientId: 'pat1', doctorId: 'doc1', status: 'accepted', paid: paid('C1') });
db.set('requests/rL', { id: 'rL', patientId: 'pat1', doctorId: 'doc1', status: 'live', paid: paid('C2') });
db.set('requests/rU', { id: 'rU', patientId: 'pat1', doctorId: 'doc1', status: 'accepted' });
db.set('requests/rD', { id: 'rD', patientId: 'pat1', doctorId: 'doc1', status: 'waiting', paid: paid('C3') });
db.set('requests/rC', { id: 'rC', patientId: 'pat1', doctorId: 'doc1', status: 'completed', paid: paid('C4') });
db.set('orders/o1', { id: 'o1', patientId: 'pat1', storeId: 'st1', status: 'ready', paid: paid('C5') });
db.set('orders/o2', { id: 'o2', patientId: 'pat1', storeId: 'st1', status: 'out', paid: paid('C6') });
db.set('orders/o3', { id: 'o3', patientId: 'pat1', storeId: 'st1', status: 'partial', paid: paid('C7') });

let r = await worker.fetch(new Request('https://w.dev/status', { headers: { Origin: 'https://healvio.web.app' } }), ENV); r = await r.json();
ok('status lists refund, readRx and reminders', r.refund === true && r.readRx === true && r.reminders === true, r);
// ---------- refunds ----------
r = await req('/pay/refund', { kind: 'fee', id: 'rA' }, '');
ok('refund: must be signed in', r[0] === 401);
r = await req('/pay/refund', { kind: 'fee', id: 'rA' }, tOther);
ok("refund: strangers can't refund", r[0] === 403);
r = await req('/pay/refund', { kind: 'fee', id: 'rU' }, tPat);
ok('refund: unpaid → nothing to refund', r[0] === 409);
r = await req('/pay/refund', { kind: 'fee', id: 'rL' }, tPat);
ok('refund: patient cannot self-refund once the consultation is live', r[0] === 409 && /already started/.test(r[1].error) && !db.get('requests/rL').refund);
r = await req('/pay/refund', { kind: 'fee', id: 'rA', reason: 'Plans changed' }, tPat);
const rfA = db.get('requests/rA');
ok('patient cancels a paid visit → full PayPal refund + cancelled', r[0] === 200 && rfA.refund.id === 'RF-C1' && rfA.refund.by === 'patient' && rfA.refund.inr === 300 && rfA.status === 'cancelled' && rfA.closedAt, rfA);
ok('refund sent to PayPal with an idempotency key and note', log.some(x => x.pp === 'POST /v2/payments/captures/C1/refund' && x.rid === 'healvio-ref-C1' && /Plans changed/.test(x.body)));
r = await req('/pay/refund', { kind: 'fee', id: 'rA' }, tPat);
ok('refund twice → "already", no second refund', r[0] === 200 && r[1].already && log.filter(x => x.pp === 'POST /v2/payments/captures/C1/refund').length === 1);
r = await req('/pay/refund', { kind: 'fee', id: 'rD', reason: 'Doctor unwell' }, tDoc);
ok('doctor cancels a paid waiting visit → refund + rejected with reason', db.get('requests/rD').status === 'rejected' && db.get('requests/rD').rejectReason === 'Doctor unwell' && db.get('requests/rD').refund.by === 'doctor');
r = await req('/pay/refund', { kind: 'fee', id: 'rC', reason: 'Goodwill' }, tAdm);
ok('admin can refund a completed visit (status kept)', r[0] === 200 && db.get('requests/rC').refund.by === 'admin' && db.get('requests/rC').status === 'completed');
r = await req('/pay/refund', { kind: 'order', id: 'o2' }, tPat);
ok('patient cannot refund medicines already on the way', r[0] === 409 && /on the way/.test(r[1].error));
r = await req('/pay/refund', { kind: 'order', id: 'o1' }, tPat);
ok('patient cancels a paid ready order → refund + cancelled', db.get('orders/o1').status === 'cancelled' && db.get('orders/o1').refund.by === 'patient');
r = await req('/pay/refund', { kind: 'order', id: 'o2', reason: 'Rider could not reach' }, tSt);
ok('store cancels an order on the way → refund + unavailable', db.get('orders/o2').status === 'unavailable' && db.get('orders/o2').refund.by === 'store');
refundMode = 'fail';
r = await req('/pay/refund', { kind: 'order', id: 'o3' }, tSt);
ok('PayPal refund error → clear message, nothing changed', r[0] === 502 && /Not enough money/.test(r[1].detail) && !db.get('orders/o3').refund && db.get('orders/o3').status === 'partial', r);
refundMode = 'full';
r = await req('/pay/refund', { kind: 'order', id: 'o3' }, tSt);
ok('already refunded at PayPal → recorded as refunded', r[0] === 200 && db.get('orders/o3').refund && db.get('orders/o3').status === 'unavailable');
refundMode = 'ok';
// ---------- read paper prescription ----------
const IMG = 'data:image/jpeg;base64,' + Buffer.from('fakejpegbytes').toString('base64');
r = await req('/read-rx', { image: IMG }, '');
ok('read-rx: must be signed in', r[0] === 401);
r = await req('/read-rx', { image: 'http://evil/x.png' }, tPat);
ok('read-rx: only photo data accepted', r[0] === 400);
r = await req('/read-rx', { image: IMG }, tPat);
ok('read-rx: Llama 4 Scout reads the medicines (empty names dropped, days cleaned)', r[0] === 200 && r[1].medicines.length === 2 && r[1].medicines[0].name === 'Augmentin 625' && r[1].medicines[0].days === '5' && r[1].readable === true, r[1]);
ok('read-rx: image sent as an image_url part', aiCalls.at(-1).input.messages[0].content[1].image_url.url === IMG);
aiMode = 'fallback';
r = await req('/read-rx', { image: IMG }, tPat);
ok('read-rx: falls back to Llama 3.2 Vision (accepts licence by itself)', r[0] === 200 && r[1].medicines[0].name === 'Dolo 650' && AI.agreed, r[1]);
aiMode = 'quota';
r = await req('/read-rx', { image: IMG }, tPat);
ok('read-rx: free limit used → 429', r[0] === 429);
aiMode = 'scout';
r = await req('/read-rx', { image: IMG }, tPat, { ...ENV, AI: undefined });
ok('read-rx: no AI binding → clear setup message', r[0] === 500 && /AI/.test(r[1].error));
// ---------- reminders ----------
const { remNext, remAt, runReminders } = W;
const TZ = -330; // India
const day = '2026-11-10';
const R = { id: 'rem1', uid: 'pat1', rxId: 'rx1', on: true, tz: TZ, times: { m: '08:00', a: '14:00', n: '21:00' },
  items: [{ name: 'Paracetamol', dose: '650 mg', note: 'after food', slots: ['m', 'n'], until: '2026-11-12' }, { name: 'Cetirizine', dose: '10 mg', slots: ['n'], until: '2026-11-10' }] };
let nx = remNext(R, remAt(day, '09:00', TZ));
ok('next reminder after 9 AM IST is 9 PM the same day', nx.k === 'n' && nx.ds === day && new Date(nx.at).toISOString() === '2026-11-10T15:30:00.000Z', nx);
nx = remNext(R, remAt(day, '21:00', TZ));
ok('after 9 PM → next morning', nx.k === 'm' && nx.ds === '2026-11-11', nx);
nx = remNext(R, remAt('2026-11-12', '21:00', TZ));
ok('after the last dose → no more reminders', nx === null);
db.set('pushTokens/pat1', { id: 'pat1', tokens: ['tokA', 'tokB'] });
db.set('reminders/rem1', { ...R, nextAt: remAt(day, '21:00', TZ) });
db.set('reminders/remOld', { ...R, id: 'remOld', nextAt: remAt('2026-11-09', '08:00', TZ) });
db.set('reminders/remOff', { ...R, id: 'remOff', on: false, nextAt: remAt(day, '21:00', TZ) });
db.set('reminders/remLater', { ...R, id: 'remLater', nextAt: remAt('2026-11-11', '08:00', TZ) });
let out = await runReminders(ENV, remAt(day, '21:01', TZ));
const msg = fcm.filter(m => m.data.tag === 'rem-rem1-2026-11-10-n');
ok('9 PM: one alert to each phone with both night medicines', msg.length === 2 && /Night medicines/.test(msg[0].data.title) && /Paracetamol 650 mg \(after food\), Cetirizine 10 mg/.test(msg[0].data.body), msg[0] && msg[0].data);
ok('next reminder set to tomorrow 8 AM', db.get('reminders/rem1').nextAt === remAt('2026-11-11', '08:00', TZ));
ok('old missed reminder (a day late) is not sent, just moved on', !fcm.some(m => /remOld/.test(m.data.tag)) && db.get('reminders/remOld').nextAt > remAt(day, '21:01', TZ));
ok('turned-off reminder: nothing sent, parked', !fcm.some(m => /remOff/.test(m.data.tag)) && db.get('reminders/remOff').nextAt === 9000000000000000);
ok('future reminder untouched', db.get('reminders/remLater').nextAt === remAt('2026-11-11', '08:00', TZ) && !db.get('reminders/remLater').sentAt);
ok('cron writes a heartbeat for the admin page', db.get('system/cron') && db.get('system/cron').at === remAt(day, '21:01', TZ) && out.due === 3, db.get('system/cron'));
const n0 = fcm.length;
db.set('reminders/rem1', { ...db.get('reminders/rem1'), nextAt: remAt(day, '21:00', TZ) });
await runReminders(ENV, remAt(day, '21:06', TZ));
ok('same reminder never sent twice', fcm.length === n0);
await runReminders(ENV, remAt('2026-11-11', '08:02', TZ));
const mm = fcm.filter(m => m.data.tag === 'rem-rem1-2026-11-11-m');
ok('next morning: only Paracetamol (Cetirizine finished)', mm.length === 2 && /Morning/.test(mm[0].data.title) && !/Cetirizine/.test(mm[0].data.body), mm[0] && mm[0].data.body);
// scheduled handler exists and uses waitUntil
let waited = null; await worker.scheduled({}, ENV, { waitUntil: p => { waited = p; } }); await waited;
ok('scheduled() runs reminders', !!waited);
console.log(`\n${pass}/${total} passed`);
if (pass !== total) process.exit(1);
