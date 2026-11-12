// consultation timer on the server (cron): time-up reminders to the doctor, delay notices to the next patients, never twice
import fs from 'fs';
const SRC = process.env.WSRC || '../healvio-app/ai-server/worker.js';
fs.writeFileSync('./worker11.mjs', fs.readFileSync(SRC, 'utf8') + '\nexport { runReminders, runConsultTimers, delayPlan };\n');
const W = await import('./worker11.mjs');
const S = crypto.subtle, RSA = { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' };
const saKeys = await S.generateKey({ ...RSA, modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]) }, true, ['sign', 'verify']);
const PID = 'healvio';
const pem = '-----BEGIN PRIVATE KEY-----\n' + Buffer.from(await S.exportKey('pkcs8', saKeys.privateKey)).toString('base64').match(/.{1,64}/g).join('\n') + '\n-----END PRIVATE KEY-----\n';
const SA = JSON.stringify({ type: 'service_account', project_id: PID, private_key_id: 'pk1', private_key: pem, client_email: 'x@healvio.iam.gserviceaccount.com' });
const enc = v => typeof v === 'string' ? { stringValue: v } : typeof v === 'number' ? { integerValue: String(v) } : typeof v === 'boolean' ? { booleanValue: v } : Array.isArray(v) ? { arrayValue: { values: v.map(enc) } } : v && typeof v === 'object' ? { mapValue: { fields: Object.fromEntries(Object.entries(v).map(([k, x]) => [k, enc(x)])) } } : { nullValue: null };
const dec = v => 'stringValue' in v ? v.stringValue : 'integerValue' in v ? Number(v.integerValue) : 'doubleValue' in v ? v.doubleValue : 'booleanValue' in v ? v.booleanValue : 'mapValue' in v ? Object.fromEntries(Object.entries(v.mapValue.fields || {}).map(([k, x]) => [k, dec(x)])) : 'arrayValue' in v ? (v.arrayValue.values || []).map(dec) : null;
const decF = f => Object.fromEntries(Object.entries(f || {}).map(([k, x]) => [k, dec(x)]));
const db = new Map(), fcm = [];
const FSB = `https://firestore.googleapis.com/v1/projects/${PID}/databases/(default)/documents`;
const J = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json' } });
let mode = {}, queries = 0;
globalThis.fetch = async (url, init = {}) => {
  url = String(url); const h = init.headers || {};
  if (url === 'https://oauth2.googleapis.com/token') return J({ access_token: 'gtok', expires_in: 3600 });
  if (url.startsWith('https://fcm.googleapis.com/')) { fcm.push(JSON.parse(init.body).message); return J({ name: 'm1' }); }
  if (h.authorization !== 'Bearer gtok') return new Response('unauth', { status: 401 });
  if (url === FSB + ':runQuery') {
    queries++;
    if (mode.queryFail) return J({ error: { code: 429 } }, 429);
    const q = JSON.parse(init.body).structuredQuery, col = q.from[0].collectionId, f = q.where.fieldFilter, fld = f.field.fieldPath, val = dec(f.value);
    const rows = [...db.entries()].filter(([k]) => k.startsWith(col + '/') && k.split('/').length === 2).map(([k, v]) => ({ k, v }))
      .filter(({ v }) => f.op === 'EQUAL' ? v[fld] === val : f.op === 'LESS_THAN_OR_EQUAL' ? v[fld] <= val : f.op === 'IN' ? val.includes(v[fld]) : false);
    return J(rows.length ? rows.map(({ k, v }) => ({ document: { name: FSB.replace('https://firestore.googleapis.com/v1/', '') + '/' + k, fields: enc(v).mapValue.fields } })) : [{ readTime: 'x' }]);
  }
  if (url.startsWith(FSB + '/')) {
    const u = new URL(url), path = decodeURIComponent(u.pathname.split('/documents/')[1]);
    if (init.method === 'POST') {
      if (mode.noteFail && path === 'notifications') return J({ error: { code: 429 } }, 429);
      const key = path + '/' + u.searchParams.get('documentId'); if (db.has(key)) return J({}, 409);
      db.set(key, init.body ? decF(JSON.parse(init.body).fields) : {}); return J({});
    }
    if (init.method === 'PATCH') { const f = JSON.parse(init.body).fields, cur = db.get(path) || {}; for (const k of u.searchParams.getAll('updateMask.fieldPaths')) cur[k] = dec(f[k]); db.set(path, cur); return J({}); }
    if (!db.has(path)) return J({}, 404);
    return J({ name: path, fields: enc(db.get(path)).mapValue.fields });
  }
  return new Response('?', { status: 500 });
};
const results = []; const ok = (n, c, x) => { results.push(!!c); console.log((c ? 'PASS ' : 'FAIL ') + n + (x !== undefined ? ' | ' + JSON.stringify(x).slice(0, 300) : '')); };
const ENV = { FIREBASE_SERVICE_ACCOUNT: SA, ALLOWED_ORIGINS: 'https://healvio.web.app' };
const NOW = Date.UTC(2026, 10, 12, 4, 50); // 10:20 AM in India
const M = 60000;
db.set('public/doc1', { id: 'doc1', name: 'Ravi Teja' });
db.set('pushTokens/doc1', { tokens: ['tdoc'] });
['pB', 'pC', 'pD', 'pE', 'pF', 'pG', 'pH'].forEach(p => db.set('pushTokens/' + p, { tokens: ['t' + p] }));
const base = { doctorId: 'doc1', slotDate: '2026-11-12', tz: -330, slotLen: 20 };
db.set('requests/rA', { ...base, id: 'rA', patientId: 'pA', patient: { name: 'Asha' }, status: 'live', slotTime: '10:00', startedAt: NOW - 21 * M });
db.set('requests/rB', { ...base, id: 'rB', patientId: 'pB', status: 'accepted', slotTime: '10:20' });
db.set('requests/rC', { ...base, id: 'rC', patientId: 'pC', status: 'waiting', slotTime: '10:40' });
db.set('requests/rD', { ...base, id: 'rD', patientId: 'pD', status: 'accepted', slotTime: '11:00' });
db.set('requests/rE', { ...base, id: 'rE', patientId: 'pE', status: 'accepted', slotTime: '12:20' }); // after a free hour: not delayed
db.set('requests/rF', { ...base, id: 'rF', patientId: 'pF', doctorId: 'doc2', status: 'accepted', slotTime: '10:20' }); // another doctor
db.set('requests/rG', { ...base, id: 'rG', patientId: 'pG', status: 'completed', slotTime: '09:40' });
db.set('requests/rH', { ...base, id: 'rH', patientId: 'pH', status: 'accepted', slotTime: '10:20', slotDate: '2026-11-13' }); // tomorrow

// the plan itself
const plan = W.delayPlan(db.get('requests/rA'), [...db.values()].filter(v => v.slotDate), NOW).map(p => p.r.id + '@' + p.to);
ok('delay plan: next three patients, booked + 10 min each; the gap stops it; others untouched', JSON.stringify(plan) === JSON.stringify(['rB@10:30', 'rC@10:50', 'rD@11:10']), plan);

// not over yet → nothing
db.set('requests/rZ', { ...base, id: 'rZ', patientId: 'pZ', doctorId: 'doc3', status: 'live', slotTime: '10:15', startedAt: NOW - 5 * M });
// left open for 7 hours → ignored
db.set('requests/rY', { ...base, id: 'rY', patientId: 'pY', doctorId: 'doc4', status: 'live', slotTime: '03:00', startedAt: NOW - 7 * 3600e3 });
// the doctor's phone already told C (fixed id): the server must not send it again
db.set('notifications/dly-rC-202611121040', { id: 'dly-rC-202611121040', to: 'pC', from: 'doc1', text: 'x', at: NOW - 1000 });

let res = await W.runReminders(ENV, NOW);
const n1 = db.get('notifications/tup1-rA');
ok('time up: doctor gets the "time is up" alert', n1 && n1.to === 'doc1' && n1.kind === 'info' && /20-minute consultation time with Asha is over/.test(n1.text) && /10 extra minutes/.test(n1.text) && n1.ref.view === 'room' && n1.ref.id === 'rA', n1);
ok('time up: the doctor\'s phone rings', fcm.some(m => m.token === 'tdoc' && m.data.title === 'Healvio · Consultation time is up' && /Asha/.test(m.data.body) && m.data.url === './?go=room&id=rA'), fcm.map(m => m.token + ':' + m.data.title));
ok('consultation marked: reminder 1 done, delay notices done', db.get('requests/rA').tup === 1 && db.get('requests/rA').dlyAt === NOW, db.get('requests/rA'));
const nB = db.get('notifications/dly-rB-202611121020'), nD = db.get('notifications/dly-rD-202611121100');
ok('patient B told: about 10 minutes late, expected 10:30 AM (booked 10:20 AM)', nB && nB.to === 'pB' && /Dr\. Ravi Teja is running about 10 minutes late/.test(nB.text) && /about 10:30 AM \(booked for 10:20 AM\)/.test(nB.text), nB && nB.text);
ok('patient D told: expected 11:10 AM', nD && /about 11:10 AM \(booked for 11:00 AM\)/.test(nD.text), nD && nD.text);
ok('booked and expected times saved on the bookings', db.get('requests/rB').delayTo === '10:30' && db.get('requests/rB').delayFor === '202611121020' && db.get('requests/rB').delayBy === 'rA' && db.get('requests/rD').delayTo === '11:10' && db.get('requests/rB').slotTime === '10:20', db.get('requests/rB'));
ok('patient C (already told by the doctor\'s phone) is not sent it again', !fcm.some(m => m.token === 'tpC') && db.get('requests/rC').delayTo === undefined);
ok('E (after a free gap), the other doctor\'s patient, a finished one and tomorrow\'s are not told', !['tpE', 'tpF', 'tpG', 'tpH'].some(t => fcm.some(m => m.token === t)) && !db.has('notifications/dly-rE-202611121220'));
ok('patients B and D phones ring once each', fcm.filter(m => m.token === 'tpB').length === 1 && fcm.filter(m => m.token === 'tpD').length === 1);
ok('not over yet and left open for hours: nothing sent', !db.has('notifications/tup1-rZ') && !db.has('notifications/tup1-rY') && !fcm.some(m => /tup1-r[YZ]/.test(m.data.tag)));
ok('the cron record counts these alerts', db.get('system/cron').timers === 3 && res.timers === 3, db.get('system/cron'));

// next minute: nothing again
let before = fcm.length;
await W.runReminders(ENV, NOW + M);
ok('next minute: no alert is sent twice', fcm.length === before, fcm.slice(before).map(m => m.data.tag));

// 10 minutes later: the stronger reminder, once
await W.runReminders(ENV, NOW + 10 * M);
const n2 = db.get('notifications/tup2-rA');
ok('10 extra minutes over: urgent reminder to the doctor', n2 && n2.kind === 'urgent' && /10 minutes over time/.test(n2.text) && /will not end by itself/.test(n2.text) && db.get('requests/rA').tup === 2, n2);
ok('urgent reminder rings with the bell title', fcm.some(m => m.token === 'tdoc' && m.data.kind === 'urgent' && m.data.title === '🔔 Healvio · Extra time is over'));
ok('the consultation is never ended by the server', db.get('requests/rA').status === 'live');
before = fcm.length;
await W.runReminders(ENV, NOW + 15 * M);
ok('later minutes: still nothing twice', fcm.length === before);

// the doctor's phone sent "time is up" first: the server only marks it
db.set('requests/rK', { ...base, id: 'rK', doctorId: 'doc5', patientId: 'pK', status: 'live', slotTime: '10:00', startedAt: NOW + 15 * M - 21 * M, dlyAt: 1 });
db.set('notifications/tup1-rK', { id: 'tup1-rK', to: 'doc5', from: 'doc5', text: 'x', at: NOW });
db.set('pushTokens/doc5', { tokens: ['tdoc5'] });
await W.runReminders(ENV, NOW + 15 * M + 30000);
ok('sent by the doctor\'s phone first: no second alert, just marked', !fcm.some(m => m.token === 'tdoc5') && db.get('requests/rK').tup === 1, db.get('requests/rK'));

// a busy database: nothing is marked, so it is tried again next minute
db.set('requests/rL', { ...base, id: 'rL', doctorId: 'doc6', patientId: 'pL', status: 'live', slotTime: '10:00', startedAt: NOW + 15 * M - 21 * M, slotDate: '2026-11-12' });
db.set('requests/rM', { ...base, id: 'rM', doctorId: 'doc6', patientId: 'pM', status: 'accepted', slotTime: '10:20' });
db.set('pushTokens/doc6', { tokens: ['tdoc6'] });
mode = { noteFail: true };
await W.runReminders(ENV, NOW + 15 * M + 40000);
ok('database busy: not marked as done', !db.get('requests/rL').tup && !db.get('requests/rL').dlyAt, db.get('requests/rL'));
mode = {};
await W.runReminders(ENV, NOW + 16 * M + 40000);
ok('next minute it goes out', db.has('notifications/tup1-rL') && db.get('requests/rL').tup === 1 && fcm.some(m => m.token === 'tdoc6'), db.get('requests/rL'));

// query fails: the rest of the cron still runs
mode = { queryFail: true };
res = await W.runReminders(ENV, NOW + 20 * M).catch(e => ({ err: String(e) }));
ok('a failed lookup does not break the cron', !res.err && db.get('system/cron').at === NOW + 20 * M, res);
mode = {};

// old consultation without a saved length: 15 minutes
db.set('requests/rN', { id: 'rN', doctorId: 'doc7', patientId: 'pN', patient: { name: 'Nina' }, status: 'live', slotDate: '2026-11-12', slotTime: '11:00', tz: -330, startedAt: NOW + 30 * M - 16 * M });
await W.runReminders(ENV, NOW + 30 * M);
ok('no saved length: 15 minutes is used', db.get('notifications/tup1-rN') && /15-minute/.test(db.get('notifications/tup1-rN').text));

const pass = results.filter(Boolean).length;
console.log(`${pass}/${results.length} passed`);
process.exit(pass === results.length ? 0 : 1);
