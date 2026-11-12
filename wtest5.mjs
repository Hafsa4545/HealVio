// PayPal payments through the worker — fake Google + fake PayPal
import worker from './worker.mjs';
const S = crypto.subtle, RSA = { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' };
const gen = () => S.generateKey({ ...RSA, modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]) }, true, ['sign', 'verify']);
const b64u = buf => Buffer.from(buf).toString('base64url');
const PID = 'healvio';
const idKeys = await gen(), saKeys = await gen();
const jwk = { ...(await S.exportKey('jwk', idKeys.publicKey)), kid: 'k1', alg: 'RS256', use: 'sig' };
const pem = '-----BEGIN PRIVATE KEY-----\n' + Buffer.from(await S.exportKey('pkcs8', saKeys.privateKey)).toString('base64').match(/.{1,64}/g).join('\n') + '\n-----END PRIVATE KEY-----\n';
const SA = JSON.stringify({ type: 'service_account', project_id: PID, private_key_id: 'pk1', private_key: pem, client_email: 'firebase-adminsdk@healvio.iam.gserviceaccount.com' });
async function idToken(uid) {
  const t = Math.floor(Date.now() / 1000);
  const h = b64u(JSON.stringify({ alg: 'RS256', kid: 'k1', typ: 'JWT' }));
  const p = b64u(JSON.stringify({ aud: PID, iss: 'https://securetoken.google.com/' + PID, sub: uid, iat: t - 10, exp: t + 3600 }));
  return h + '.' + p + '.' + b64u(await S.sign(RSA, idKeys.privateKey, Buffer.from(h + '.' + p)));
}
const enc = v => typeof v === 'string' ? { stringValue: v } : typeof v === 'number' ? (Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v }) : typeof v === 'boolean' ? { booleanValue: v } : Array.isArray(v) ? { arrayValue: { values: v.map(enc) } } : v && typeof v === 'object' ? { mapValue: { fields: Object.fromEntries(Object.entries(v).map(([k, x]) => [k, enc(x)])) } } : { nullValue: null };
const dec = v => 'stringValue' in v ? v.stringValue : 'integerValue' in v ? Number(v.integerValue) : 'doubleValue' in v ? v.doubleValue : 'booleanValue' in v ? v.booleanValue : 'mapValue' in v ? Object.fromEntries(Object.entries(v.mapValue.fields || {}).map(([k, x]) => [k, dec(x)])) : 'arrayValue' in v ? (v.arrayValue.values || []).map(dec) : null;
const db = new Map(), log = [];
const FSB = `https://firestore.googleapis.com/v1/projects/${PID}/databases/(default)/documents/`;
// fake PayPal
const PPB = 'https://api-m.sandbox.paypal.com', PPL = 'https://api-m.paypal.com';
const orders = new Map(); let seq = 0, oauthCalls = 0, declineNext = false, pendingNext = false;
const J = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json' } });
globalThis.fetch = async (url, init = {}) => {
  url = String(url); const h = init.headers || {};
  if (url.startsWith('https://www.googleapis.com/service_accounts/v1/jwk/securetoken')) return new Response(JSON.stringify({ keys: [jwk] }), { headers: { 'cache-control': 'public, max-age=20000' } });
  if (url === 'https://oauth2.googleapis.com/token') return J({ access_token: 'gtok', expires_in: 3600 });
  if (url.startsWith(PPB) || url.startsWith(PPL)) {
    const live = url.startsWith(PPL), path = url.slice((live ? PPL : PPB).length);
    log.push({ pp: init.method + ' ' + path, live, rid: h['PayPal-Request-Id'] });
    if (path === '/v1/oauth2/token') {
      oauthCalls++;
      const [id, sec] = Buffer.from(String(h.authorization).replace('Basic ', ''), 'base64').toString().split(':');
      if (id !== 'CID' || sec !== 'SECRET') return J({ error: 'invalid_client', error_description: 'Client Authentication failed' }, 401);
      return J({ access_token: 'pptok', expires_in: 32400 });
    }
    if (h.authorization !== 'Bearer pptok') return J({ name: 'AUTHENTICATION_FAILURE' }, 401);
    if (path === '/v2/checkout/orders' && init.method === 'POST') {
      const b = JSON.parse(init.body), id = 'PPO' + (++seq);
      orders.set(id, { id, status: 'CREATED', purchase_units: b.purchase_units.map(u => ({ ...u })), body: b });
      return J({ id, status: 'CREATED', links: [{ rel: 'self', href: 'https://api-m.sandbox.paypal.com/v2/checkout/orders/' + id }, { rel: 'approve', href: 'https://www.sandbox.paypal.com/checkoutnow?token=' + id }] }, 201);
    }
    let m = /^\/v2\/checkout\/orders\/([\w-]+)\/capture$/.exec(path);
    if (m) {
      const o = orders.get(m[1]); if (!o) return J({ name: 'RESOURCE_NOT_FOUND', details: [{ issue: 'INVALID_RESOURCE_ID' }] }, 404);
      if (o.status === 'COMPLETED') return J({ name: 'UNPROCESSABLE_ENTITY', details: [{ issue: 'ORDER_ALREADY_CAPTURED' }] }, 422);
      if (o.status !== 'APPROVED') return J({ name: 'UNPROCESSABLE_ENTITY', details: [{ issue: 'ORDER_NOT_APPROVED' }] }, 422);
      if (declineNext) { declineNext = false; return J({ name: 'UNPROCESSABLE_ENTITY', details: [{ issue: 'INSTRUMENT_DECLINED' }] }, 422); }
      const st = pendingNext ? 'PENDING' : 'COMPLETED'; pendingNext = false;
      o.status = 'COMPLETED';
      o.purchase_units = o.purchase_units.map(u => ({ reference_id: u.reference_id, payments: { captures: [{ id: 'CAP-' + o.id, status: st, amount: u.amount, custom_id: u.custom_id }] } }));
      return J({ id: o.id, status: 'COMPLETED', purchase_units: o.purchase_units }, 201);
    }
    m = /^\/v2\/checkout\/orders\/([\w-]+)$/.exec(path);
    if (m && init.method === 'GET') { const o = orders.get(m[1]); return o ? J({ id: o.id, status: o.status, purchase_units: o.purchase_units }) : J({}, 404); }
    return J({ name: 'NOT_FOUND' }, 404);
  }
  if (h.authorization !== 'Bearer gtok') return new Response('unauth', { status: 401 });
  if (url.startsWith(FSB)) {
    const u = new URL(url), path = decodeURIComponent(u.pathname.split('/documents/')[1]);
    if (init.method === 'PATCH') {
      if (u.searchParams.get('currentDocument.exists') === 'true' && !db.has(path)) return new Response('{}', { status: 404 });
      const f = JSON.parse(init.body).fields, cur = db.get(path) || {};
      for (const k of u.searchParams.getAll('updateMask.fieldPaths')) cur[k] = dec(f[k]);
      db.set(path, cur); log.push({ fsPatch: path, mask: u.searchParams.getAll('updateMask.fieldPaths') }); return new Response('{}');
    }
    if (!db.has(path)) return new Response('{}', { status: 404 });
    return J({ name: path, fields: enc(db.get(path)).mapValue.fields });
  }
  return new Response('?', { status: 500 });
};
const approve = id => { orders.get(id).status = 'APPROVED'; };
const ENV = { ALLOWED_ORIGINS: 'https://healvio.web.app', FIREBASE_SERVICE_ACCOUNT: SA, PAYPAL_CLIENT_ID: ' CID ', PAYPAL_CLIENT_SECRET: 'SECRET' };
const req = async (path, body, tok, method = 'POST', e = ENV, origin = 'https://healvio.web.app') => { const r = await worker.fetch(new Request('https://w.dev' + path, { method, headers: { Origin: origin, 'content-type': 'application/json', ...(tok ? { authorization: 'Bearer ' + tok } : {}) }, body: method === 'POST' ? JSON.stringify(body) : undefined }), e); return [r.status, await r.json()]; };
let pass = 0, total = 0;
const ok = (n, c, x = '') => { total++; if (c) pass++; console.log((c ? 'PASS ' : 'FAIL ') + n, x === '' ? '' : '| ' + JSON.stringify(x).slice(0, 260)); };
const tPat = await idToken('pat1'), tPat2 = await idToken('pat2'), tStore = await idToken('st1');

db.set('public/doc1', { id: 'doc1', name: 'Dr. Asha Rao', role: 'doctor', doc: { fee: 500 } });
db.set('public/doc0', { id: 'doc0', name: 'Dr. Free', role: 'doctor', doc: { fee: 0 } });
db.set('requests/rA', { id: 'rA', patientId: 'pat1', doctorId: 'doc1', status: 'accepted' });
db.set('requests/rB', { id: 'rB', patientId: 'pat1', doctorId: 'doc1', status: 'live' });
db.set('requests/rReq', { id: 'rReq', patientId: 'pat1', doctorId: 'doc1', status: 'requested' });
db.set('requests/rFree', { id: 'rFree', patientId: 'pat1', doctorId: 'doc0', status: 'accepted' });
db.set('orders/o1', { id: 'o1', patientId: 'pat1', storeId: 'st1', storeName: 'Sri Ram Medicals', status: 'ready', total: 349.5 });
db.set('orders/oSent', { id: 'oSent', patientId: 'pat1', storeId: 'st1', status: 'sent' });
db.set('orders/oNoPrice', { id: 'oNoPrice', patientId: 'pat1', storeId: 'st1', status: 'partial' });

let r = await req('/status', null, null, 'GET');
ok('status tells the app PayPal is on (sandbox, USD, rate 95)', r[1].paypal && r[1].paypal.clientId === 'CID' && r[1].paypal.env === 'sandbox' && r[1].paypal.currency === 'USD' && r[1].paypal.rate === 95, r[1]);
r = await req('/status', null, null, 'GET', { ...ENV, PAYPAL_CLIENT_SECRET: '' });
ok('status: PayPal off until both keys are added', r[1].paypal === false, r[1]);
r = await req('/status', null, null, 'GET', { ...ENV, PAYPAL_ENV: 'live', INR_RATE: '90' });
ok('status: live mode and custom rate', r[1].paypal.env === 'live' && r[1].paypal.rate === 90, r[1]);

r = await req('/pay/create', { kind: 'fee', id: 'rA' }, '');
ok('create: must be signed in', r[0] === 401, r);
r = await req('/pay/create', { kind: 'fee', id: 'rA' }, tPat, 'POST', ENV, 'https://evil.example');
ok('create: other websites refused', r[0] === 403, r);
r = await req('/pay/create', { kind: 'fee', id: 'rA' }, tPat2);
ok("create: can't pay someone else's consultation", r[0] === 403, r);
r = await req('/pay/create', { kind: 'fee', id: 'rReq' }, tPat);
ok('create: only after the doctor accepts', r[0] === 409 && /accepts/.test(r[1].error), r);
r = await req('/pay/create', { kind: 'fee', id: 'rFree' }, tPat);
ok('create: doctor with no fee → nothing to pay', r[0] === 409, r);
r = await req('/pay/create', { kind: 'weird', id: 'rA' }, tPat);
ok('create: unknown kind refused', r[0] === 400, r);

r = await req('/pay/create', { kind: 'fee', id: 'rA', amount: '0.01' }, tPat);
const o1 = orders.get(r[1].orderID);
ok('create: price comes from the database (₹500 → US$5.26), not from the phone', r[0] === 200 && r[1].value === '5.26' && o1.purchase_units[0].amount.value === '5.26' && o1.purchase_units[0].amount.currency_code === 'USD', [r[1], o1 && o1.purchase_units[0].amount]);
ok('create: order is labelled for this consultation and patient', o1.purchase_units[0].reference_id === 'fee:rA' && o1.purchase_units[0].custom_id === 'fee:rA:pat1' && /Dr\. Asha Rao/.test(o1.purchase_units[0].description) && o1.body.application_context.shipping_preference === 'NO_SHIPPING');
ok('create: uses the sandbox in test mode and trims the client id', log.some(x => x.pp === 'POST /v2/checkout/orders' && !x.live));

// PayPal's own page and back (for the installed app)
let rr = await req('/pay/create', { kind: 'fee', id: 'rA', redirect: true, back: 'https://healvio.web.app/' }, tPat);
const og = orders.get(rr[1].orderID);
ok('PayPal page: approval link returned and PayPal brings the payer back to Healvio', rr[0] === 200 && rr[1].approve === 'https://www.sandbox.paypal.com/checkoutnow?token=' + rr[1].orderID && og.body.application_context.return_url === 'https://healvio.web.app/?paypal=ok&pk=fee&pi=rA' && og.body.application_context.cancel_url === 'https://healvio.web.app/?paypal=cancel&pk=fee&pi=rA', [rr[1], og && og.body.application_context]);
rr = await req('/pay/create', { kind: 'fee', id: 'rA', redirect: true, back: 'https://evil.example/steal' }, tPat);
ok('PayPal page: never sends the payer back to another website', rr[0] === 400, rr);
rr = await req('/pay/create', { kind: 'fee', id: 'rA', redirect: true, back: 'http://healvio.web.app/' }, tPat);
ok('PayPal page: only a secure (https) way back', rr[0] === 400, rr);
ok('button in the sheet (no redirect): no way-back address, no link', !('return_url' in o1.body.application_context) && !('approve' in (r[1] || {})));
r = await req('/pay/capture', { kind: 'fee', id: 'rA', orderID: o1.id }, tPat);
ok('capture before approval: refused, nothing marked paid', r[0] === 502 && !db.get('requests/rA').paid, r);
approve(o1.id);
r = await req('/pay/capture', { kind: 'fee', id: 'rA', orderID: o1.id }, tPat);
const pA = db.get('requests/rA').paid;
ok('capture: money taken and consultation marked paid', r[0] === 200 && r[1].ok && pA && pA.by === 'paypal' && pA.amount === '5.26' && pA.currency === 'USD' && pA.inr === 500 && pA.captureId === 'CAP-' + o1.id && pA.test === true, [r, pA]);
ok('capture: idempotency key sent to PayPal', log.some(x => x.pp === `POST /v2/checkout/orders/${o1.id}/capture` && x.rid === 'healvio-cap-' + o1.id));
ok('capture: only paid + updatedAt written', log.filter(x => x.fsPatch).slice(-1)[0].mask.join() === 'paid,updatedAt');
r = await req('/pay/capture', { kind: 'fee', id: 'rA', orderID: o1.id }, tPat);
ok('capture again: says already paid, no double charge', r[0] === 200 && r[1].already === true, r);
r = await req('/pay/create', { kind: 'fee', id: 'rA' }, tPat);
ok('create after paid: already paid', r[0] === 200 && r[1].already === true && !r[1].orderID, r);

// reuse a paid PayPal order for another consultation
r = await req('/pay/capture', { kind: 'fee', id: 'rB', orderID: o1.id }, tPat);
ok("can't reuse one payment for another consultation", r[0] === 409 && !db.get('requests/rB').paid, r);

// cheap order made outside Healvio (client-side) with the right label
orders.set('CHEAP', { id: 'CHEAP', status: 'APPROVED', purchase_units: [{ reference_id: 'fee:rB', custom_id: 'fee:rB:pat1', amount: { currency_code: 'USD', value: '0.01' } }] });
r = await req('/pay/capture', { kind: 'fee', id: 'rB', orderID: 'CHEAP' }, tPat);
ok('underpaying (₹1 order made outside the app) is not marked paid', r[0] === 409 && /amount/.test(r[1].error) && !db.get('requests/rB').paid, r);

// declined card
r = await req('/pay/create', { kind: 'fee', id: 'rB' }, tPat); approve(r[1].orderID); declineNext = true;
const oB = r[1].orderID;
r = await req('/pay/capture', { kind: 'fee', id: 'rB', orderID: oB }, tPat);
ok('declined card: 402 with retry so the buyer can pick another way', r[0] === 402 && r[1].retry === true && !db.get('requests/rB').paid, r);
r = await req('/pay/capture', { kind: 'fee', id: 'rB', orderID: oB }, tPat);
ok('second try after decline: paid', r[0] === 200 && db.get('requests/rB').paid.amount === '5.26', r);

// pending (e.g. eCheck)
db.set('requests/rC', { id: 'rC', patientId: 'pat1', doctorId: 'doc1', status: 'completed' });
r = await req('/pay/create', { kind: 'fee', id: 'rC' }, tPat); approve(r[1].orderID); pendingNext = true;
r = await req('/pay/capture', { kind: 'fee', id: 'rC', orderID: r[1].orderID }, tPat);
ok('pending capture is not marked paid', r[0] === 409 && /still checking/.test(r[1].error) && !db.get('requests/rC').paid, r);

// medicine orders
r = await req('/pay/create', { kind: 'order', id: 'oSent' }, tPat);
ok("order: can't pay before the store confirms", r[0] === 409, r);
r = await req('/pay/create', { kind: 'order', id: 'oNoPrice' }, tPat);
ok('order: needs a price from the store', r[0] === 409 && /price/.test(r[1].error), r);
r = await req('/pay/create', { kind: 'order', id: 'o1' }, tStore);
ok("order: the store can't pay the patient's order", r[0] === 403, r);
r = await req('/pay/create', { kind: 'order', id: 'o1' }, tPat);
const oo = orders.get(r[1].orderID);
ok('order: ₹349.50 → US$3.68 with store name', r[1].value === '3.68' && oo.purchase_units[0].reference_id === 'order:o1' && /Sri Ram Medicals/.test(oo.purchase_units[0].description), r[1]);
approve(oo.id);
r = await req('/pay/capture', { kind: 'order', id: 'o1', orderID: oo.id }, tPat);
const pO = db.get('orders/o1').paid;
ok('order: paid and recorded', r[0] === 200 && pO && pO.inr === 349.5 && pO.amount === '3.68', [r, pO]);

// wrong keys → clear message
db.set('requests/rD', { id: 'rD', patientId: 'pat1', doctorId: 'doc1', status: 'accepted' });
r = await req('/pay/create', { kind: 'fee', id: 'rD' }, tPat, 'POST', { ...ENV, PAYPAL_CLIENT_ID: 'WRONG' });
ok('wrong PayPal keys: clear error', r[0] === 502 && /PAYPAL_CLIENT_ID/.test(r[1].detail), r);
// live mode goes to the live PayPal
r = await req('/pay/create', { kind: 'fee', id: 'rD' }, tPat, 'POST', { ...ENV, PAYPAL_ENV: 'live', INR_RATE: '100' });
ok('live mode uses api-m.paypal.com and the custom rate (₹500 → $5.00)', r[0] === 200 && r[1].value === '5.00' && log.some(x => x.pp === 'POST /v2/checkout/orders' && x.live), r);
// INR currency
r = await req('/pay/create', { kind: 'fee', id: 'rD' }, tPat, 'POST', { ...ENV, PAY_CURRENCY: 'inr' });
ok('INR currency charges rupees directly', r[1].value === '500.00' && r[1].currency === 'INR', r[1]);
// no keys
r = await req('/pay/create', { kind: 'fee', id: 'rD' }, tPat, 'POST', { ALLOWED_ORIGINS: ENV.ALLOWED_ORIGINS, FIREBASE_SERVICE_ACCOUNT: SA });
ok('without PayPal keys: clear setup message', r[0] === 500 && /PAYPAL_CLIENT_ID/.test(r[1].error), r);
ok('PayPal sign-in token is reused (few logins)', oauthCalls <= 4, oauthCalls);
// earlier features still answer
r = await req('/status', null, null, 'GET');
ok('status still reports push', r[1].push === true, r[1]);

console.log(`\n${pass}/${total} passed`);
if (pass !== total) process.exit(1);
