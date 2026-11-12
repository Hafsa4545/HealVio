// refunds, paper prescription reading, medicine reminders
import fs from 'fs';
fs.writeFileSync('./worker8.mjs', fs.readFileSync('../healvio-app/ai-server/worker.js', 'utf8') + '\nexport { runReminders, runPayReminders, cleanSpeech, cleanSummary };\n');
const W = await import('./worker8.mjs');
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
  if (url.startsWith(PPB)) return J({ access_token: 'pptok', expires_in: 32400 });
  if (url.startsWith('https://fcm.googleapis.com/')) { fcm.push(JSON.parse(init.body).message); return J({ name: 'm1' }); }
  if (h.authorization !== 'Bearer gtok') return new Response('unauth', { status: 401 });
  const RQ = /^(.*):runQuery$/.exec(url);
  if (RQ) {
    const q = JSON.parse(init.body).structuredQuery, parent = RQ[1].replace(FSB, '').replace(/^\//, ''), col = q.from[0].collectionId;
    let rows = [...db.entries()].filter(([k]) => { const pre = (parent ? parent + '/' : '') + col + '/'; return k.startsWith(pre) && !k.slice(pre.length).includes('/'); });
    const ff = q.where && q.where.fieldFilter;
    if (ff && ff.op === 'IN') { const vals = ff.value.arrayValue.values.map(v => v.stringValue); rows = rows.filter(([, v]) => vals.includes(v[ff.field.fieldPath])); }
    if (ff && ff.op === 'LESS_THAN_OR_EQUAL') rows = rows.filter(([, v]) => Number(v[ff.field.fieldPath]) <= Number(ff.value.integerValue));
    if (q.orderBy) rows.sort((a, b) => Number(a[1].at) - Number(b[1].at));
    if (q.startAt) rows = rows.filter(([, v]) => Number(v.at) > Number(q.startAt.values[0].integerValue));
    rows = rows.slice(0, q.limit || 1000);
    log.push({ query: col, parent, n: rows.length });
    return J(rows.length ? rows.map(([k, v]) => ({ document: { name: FSB + '/' + k, fields: enc(v).mapValue.fields } })) : [{ readTime: 'x' }]);
  }
  if (url.startsWith(FSB + '/')) {
    const u = new URL(url), path = decodeURIComponent(u.pathname.split('/documents/')[1]);
    if (init.method === 'POST') { const id = u.searchParams.get('documentId'); const key = path + '/' + id; if (db.has(key)) return J({}, 409); db.set(key, init.body && JSON.parse(init.body).fields ? Object.fromEntries(Object.entries(JSON.parse(init.body).fields).map(([k, v]) => [k, dec(v)])) : {}); return J({}); }
    if (init.method === 'PATCH') {
      if (u.searchParams.get('currentDocument.exists') === 'true' && !db.has(path)) return J({}, 404);
      const f = JSON.parse(init.body).fields, cur = db.get(path) || {};
      for (const k of u.searchParams.getAll('updateMask.fieldPaths')) cur[k] = dec(f[k]);
      db.set(path, cur); log.push({ fsPatch: path }); return J({});
    }
    if (!db.has(path)) return J({}, 404);
    return J({ name: path, fields: enc(db.get(path)).mapValue.fields });
  }
  return new Response('?', { status: 500 });
};
const results = []; const ok = (n, c, x) => { results.push(!!c); console.log((c ? 'PASS ' : 'FAIL ') + n + (x !== undefined ? ' | ' + JSON.stringify(x).slice(0, 300) : '')); };
let aiMode = 'ok';
const aiCalls = [];
const AI = { async run(model, input) {
  aiCalls.push({ model, input });
  if (aiMode === 'quota') throw new Error('3036: daily free allocation of 10,000 neurons used');
  if (model.includes('whisper') && aiMode === 'icelandic' && !input.language) return { text: ' Það er nú aftur ný. ', transcription_info: { language: 'is' }, segments: [{ text: ' Það er nú aftur ný.', avg_logprob: -0.5, no_speech_prob: 0.1, compression_ratio: 1.2 }] };
  if (model.includes('whisper') && aiMode === 'icelandic' && input.language === 'en') return { text: ' I have had fever for two days. ', transcription_info: { language: 'en' }, segments: [{ text: ' Hi, guys,', avg_logprob: -0.4, no_speech_prob: 0.2, compression_ratio: 1.1 }, { text: ' I have had fever for two days.', avg_logprob: -0.3, no_speech_prob: 0.05, compression_ratio: 1.2 }] };
  if (model.includes('whisper') && aiMode === 'named') return { text: ' My head hurts. ', transcription_info: { language: 'english' }, segments: [{ text: ' My head hurts.', avg_logprob: -0.3, no_speech_prob: 0.05, compression_ratio: 1.1 }] };
  if (model.includes('whisper') && aiMode === 'foreign') return { text: ' Enginn þig að verð. ', transcription_info: { language: input.language || 'is' }, segments: [{ text: ' Enginn þig að verð.', avg_logprob: -0.5, no_speech_prob: 0.1, compression_ratio: 1.2 }] };
  if (model.includes('whisper')) return { text: ' I have fever fever fever fever since 3 days. ', transcription_info: { language: input.language || 'en' },
    segments: [{ text: ' I have fever fever fever fever since 3 days.', avg_logprob: -0.3, no_speech_prob: 0.05, compression_ratio: 1.3 }, { text: ' Thank you for watching!', avg_logprob: -0.4, no_speech_prob: 0.3 }, { text: ' zzz zzz', avg_logprob: -1.3, no_speech_prob: 0.9 }] };
  const p = input.messages[1].content;
  if (p.startsWith('Translate every text value')) {
    const g = JSON.parse(p.slice(p.indexOf('\n\n') + 2));
    if (aiMode === 'transfail' && 'tests' in g) return { response: 'sorry' };
    const tr = v => typeof v === 'string' ? (v ? 'తె ' + v : v) : Array.isArray(v) ? v.map(tr) : v && typeof v === 'object' ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, tr(x)])) : v;
    return { response: JSON.stringify(tr(g)) };
  }
  if (p.includes('Write precise notes')) return { response: '{"notes":["[00:10] Patient: fever 3 days","[40:00] Doctor: take Dolo 650 twice a day for 3 days"]}' };
  if (p.startsWith('Check this AI summary')) {
    if (aiMode === 'badcheck') return { response: 'sorry, cannot' };
    const d = JSON.parse(p.split('SUMMARY:\n')[1].split('\n\nConsultation type')[0]);
    d.medicines = d.medicines.map(m => m.name === 'Dolo' ? { ...m, name: 'Dolo 650', dose: '650 mg' } : m); // fixes a name from the prescription
    d.key_points = d.key_points.filter(x => !x.includes('invented'));
    return { response: JSON.stringify(d) };
  }
  if (p.includes('Write an accurate summary')) {
    if (aiMode === 'array') return { response: { summary: 'Object answer works.', medicines: [] } };
    return { response: 'Sure!\n' + JSON.stringify({ summary: 'You had fever for 3 days. The doctor said it is a viral fever.', chief_complaint: 'Fever for 3 days', symptoms: ['Fever for 3 days', 'Body pain'],
      diagnosis: 'Viral fever', medicines: [{ name: 'Dolo', dose: '', timing: '1-0-1', days: '3', instructions: 'after food' }, { name: '' }], tests: ['CBC blood test'], key_points: ['Drink plenty of water', 'an invented point'],
      warning_signs: ['Fever above 103 F'], follow_up: 'After 3 days', doctor_note: { s: 'Fever 3d', o: '', a: 'Viral fever', p: 'Dolo 650 BD x3d, CBC' } }) };
  }
  return { response: '{}' };
} };
const env = { ALLOWED_ORIGINS: 'https://healvio.web.app', FIREBASE_SERVICE_ACCOUNT: SA, AI, PAYPAL_CLIENT_ID: 'CID', PAYPAL_CLIENT_SECRET: 'SEC' };
const call = async (path, body, uid, e = env) => { const r = await worker.fetch(new Request('https://w.dev' + path, { method: 'POST', headers: { Origin: 'https://healvio.web.app', 'content-type': 'application/json', authorization: 'Bearer ' + (uid ? await idToken(uid) : 'x') }, body: JSON.stringify(body) }), e, { waitUntil() {} }); return [r.status, await r.json()]; };
const T = Date.now();
db.set('public/doc1', { name: 'Ananya Rao', doc: { system: 'Allopathy', specialization: 'General Physician', fee: 300 } });
db.set('accounts/pat1', { name: 'Ravi Kumar', age: 35, gender: 'Male' });
db.set('requests/r1', { id: 'r1', doctorId: 'doc1', patientId: 'pat1', status: 'completed', problem: 'fever and body pain', startedAt: T - 3600e3, rxId: 'rx1' });
db.set('prescriptions/rx1', { medicines: [{ name: 'Dolo 650', dose: '650 mg', freq: '1-0-1', days: '3', note: 'after food' }], diagnosis: 'Viral fever', followUp: '3 days' });
db.set('requests/r1/messages/m1', { from: 'pat1', text: 'I have fever for 3 days', at: T - 3590e3 });
db.set('requests/r1/messages/m2', { from: 'doc1', text: 'Take Dolo twice a day after food', stt: true, at: T - 3500e3 });
db.set('requests/r1/messages/m3', { from: 'system', sys: true, text: 'Consultation ended.', at: T - 3400e3 });
db.set('requests/r1/messages/m4', { from: 'system', sys: true, text: 'Payment received', at: T - 3300e3 });
db.set('pushTokens/pat1', { tokens: ['tokP'] });

// ---- /status ----
const st = await (await worker.fetch(new Request('https://w.dev/status', { headers: { Origin: 'https://healvio.web.app' } }), env)).json();
ok('status says the server summary is available', st.summary === true);

// ---- /summary ----
let [code, j] = await call('/summary', { rid: 'r1', lang: 'English' }, 'pat1');
ok('patient gets a summary', code === 200 && j.summary && j.summary.summary.startsWith('You had fever'), [code, j.error]);
const prompt1 = aiCalls.find(c => c.input.messages && c.input.messages[1].content.includes('Write an accurate summary')).input.messages[1].content;
ok('summary reads the chat AND the call notes in time order', /\[00:10\] Patient: I have fever for 3 days\n\[01:40\] Doctor \(on call\): Take Dolo twice a day after food/.test(prompt1), prompt1.slice(prompt1.indexOf('Conversation'), prompt1.indexOf('Conversation') + 200));
ok('summary uses the prescription, the patient age and the doctor type', prompt1.includes('- Dolo 650 | dose: 650 mg | timing: 1-0-1 | days: 3 | after food') && prompt1.includes('age 35') && prompt1.includes('General Physician'));
ok('system messages other than start/end/call are left out', !prompt1.includes('Payment received') && prompt1.includes('Consultation ended.'));
ok('check step fixed the medicine name from the prescription', j.summary.medicines.length === 1 && j.summary.medicines[0].name === 'Dolo 650' && j.summary.medicines[0].dose === '650 mg', j.summary.medicines);
ok('check step removed a made-up point', j.summary.key_points.length === 1 && j.summary.key_points[0] === 'Drink plenty of water');
ok('rich fields kept: tests, warning signs, SOAP note', j.summary.tests[0] === 'CBC blood test' && j.summary.warning_signs[0] === 'Fever above 103 F' && j.summary.doctor_note.a === 'Viral fever');
ok('saved on the consultation by the server', db.get('requests/r1').aiSummary && db.get('requests/r1').aiSummary.diagnosis === 'Viral fever' && db.get('requests/r1').aiSummary.steps === 2);
ok('low temperature for accuracy', aiCalls.filter(c => c.input.messages).every(c => c.input.temperature <= 0.1));
ok('a stranger cannot get the summary', (await call('/summary', { rid: 'r1' }, 'someone'))[0] === 403);
db.set('requests/r2', { id: 'r2', doctorId: 'doc1', patientId: 'pat1', status: 'accepted', problem: 'x' });
ok('not before the consultation starts', (await call('/summary', { rid: 'r2' }, 'pat1'))[0] === 409);
aiMode = 'badcheck'; aiCalls.length = 0;
[code, j] = await call('/summary', { rid: 'r1' }, 'pat1');
ok('if the check step fails, the first summary is still saved', code === 200 && j.summary.medicines[0].name === 'Dolo');
aiMode = 'ok'; aiCalls.length = 0;
[code, j] = await call('/summary', { rid: 'r1', lang: 'Telugu' }, 'pat1');
const SM = j.summary;
ok('Telugu: written and checked in English first', aiCalls.some(c => c.input.messages && c.input.messages[1].content.includes('for the patient in English')));
ok('Telugu: EVERY part is translated (summary, symptoms, tests, points, warning signs, follow-up)', SM.lang === 'Telugu' && SM.summary.startsWith('తె ') && SM.symptoms.every(x => x.startsWith('తె ')) && SM.tests.every(x => x.startsWith('తె ')) && SM.key_points.every(x => x.startsWith('తె ')) && SM.warning_signs.every(x => x.startsWith('తె ')) && SM.follow_up.startsWith('తె '), SM);
ok('Telugu: headings translated too', SM.labels && SM.labels.medicines === 'తె Your medicines' && SM.labels.none.startsWith('తె '), SM.labels);
ok('Telugu: medicine name and dose stay exactly; timing and instructions translated', SM.medicines[0].name === 'Dolo 650' && SM.medicines[0].dose === '650 mg' && SM.medicines[0].instructions.startsWith('తె '), SM.medicines);
ok("Telugu: doctor's SOAP note stays English", SM.doctor_note.a === 'Viral fever');
ok('Telugu: 3 parts translated', SM.translated === '3/3');
aiMode = 'transfail';
[code, j] = await call('/summary', { rid: 'r1', lang: 'Telugu' }, 'pat1');
ok('if one part fails to translate, the rest is still translated', j.summary.translated === '2/3' && j.summary.summary.startsWith('తె ') && j.summary.tests[0] === 'CBC blood test');
aiMode = 'ok';
db.set('requests/rB', { id: 'rB', doctorId: 'doc1', patientId: 'pat1', status: 'completed', problem: 'x' });
db.set('requests/rB/messages/b1', { from: 'pat1', text: 'hello', at: T });
const cleaned = await W.cleanSummary({ summary: 'ok', follow_up: '-', diagnosis: 'Not mentioned', symptoms: ['-', 'fever'], medicines: [{ name: 'Polo', dose: '-', timing: '2 times a day', days: '-', instructions: '' }] }, 'English');
ok('"-" and "not mentioned" become empty (no dashes on screen)', cleaned.follow_up === '' && cleaned.diagnosis === '' && cleaned.symptoms.length === 1 && cleaned.medicines[0].dose === '' && cleaned.medicines[0].days === '', cleaned);
aiMode = 'array';
[code, j] = await call('/summary', { rid: 'r1' }, 'pat1');
ok('works when the AI answers with an object', code === 200 && j.summary.summary === 'Object answer works.');
aiMode = 'ok'; fcm.length = 0;
[code, j] = await call('/summary', { rid: 'r1', notify: true }, 'doc1');
ok('doctor-triggered summary alerts the patient (in app + phone)', code === 200 && [...db.keys()].some(k => k.startsWith('notifications/nsumr1')) && fcm.some(m => m.data.title === 'Healvio · Consultation summary'), fcm.map(m => m.data.title));
fcm.length = 0;
await call('/summary', { rid: 'r1', notify: true }, 'doc1');
ok('…only once', fcm.length === 0);
// long consultation → notes part by part
for (let i = 0; i < 400; i++) db.set('requests/r1/messages/x' + String(i).padStart(3, '0'), { from: i % 2 ? 'doc1' : 'pat1', text: 'Long talk about symptoms and medicines number ' + i + ' ' + 'detail-'.repeat(12) + 'end.', at: T - 3000e3 + i * 1000 });
aiCalls.length = 0;
[code, j] = await call('/summary', { rid: 'r1' }, 'pat1');
const noteCalls = aiCalls.filter(c => c.input.messages && c.input.messages[1].content.includes('Write precise notes')).length;
ok('long consultation: read in parts, nothing cut off', code === 200 && noteCalls >= 2 && aiCalls.some(c => c.input.messages && c.input.messages[1].content.includes('Notes taken from the whole consultation')), noteCalls);
aiMode = 'quota';
ok('free limit used up → clear 429', (await call('/summary', { rid: 'r1' }, 'pat1'))[0] === 429);
aiMode = 'ok';

// ---- /listen ----
db.set('requests/rL', { id: 'rL', doctorId: 'doc1', patientId: 'pat1', status: 'live', problem: 'cough and cold', rxId: 'rx1' });
aiCalls.length = 0;
[code, j] = await call('/listen', { rid: 'rL', audio: 'A'.repeat(2000), prev: 'Doctor asked about the cough.', lang: 'te' }, 'pat1');
const wi = aiCalls.find(c => c.model.includes('whisper')).input;
ok('call notes: medical context and medicine names help speech-to-text', wi.initial_prompt.includes('General Physician') && wi.initial_prompt.includes('cough and cold') && wi.initial_prompt.includes('Dolo 650') && wi.initial_prompt.endsWith('Doctor asked about the cough.'), wi.initial_prompt);
ok('call notes: the language you chose is used', wi.language === 'te' && wi.vad_filter === true);
ok('call notes: stuck repeats and made-up phrases removed', j.text === 'I have fever since 3 days.', j.text);
[code, j] = await call('/listen', { rid: 'rL', audio: 'A'.repeat(2000), lang: 'xx' }, 'pat1');
ok('unknown language → auto', !('language' in aiCalls[aiCalls.length - 1].input));
aiMode = 'icelandic'; aiCalls.length = 0;
[code, j] = await call('/listen', { rid: 'rL', audio: 'A'.repeat(2000) }, 'pat1');
ok('Indian speech heard as Icelandic → heard again in English', j.text === 'I have had fever for two days.' && j.lang === 'en' && aiCalls.filter(c => c.model.includes('whisper')).length === 2 && aiCalls.filter(c => c.model.includes('whisper'))[1].input.language === 'en', [j, aiCalls.length]);
aiMode = 'foreign'; aiCalls.length = 0;
[code, j] = await call('/listen', { rid: 'rL', audio: 'A'.repeat(2000) }, 'pat1');
ok('still foreign letters after the second try → nothing written (no wrong sentences)', code === 200 && j.text === '', j);
aiMode = 'named'; aiCalls.length = 0;
[code, j] = await call('/listen', { rid: 'rL', audio: 'A'.repeat(2000) }, 'pat1');
ok('English named "english" → heard once (no extra cost)', j.text === 'My head hurts.' && j.lang === 'en' && aiCalls.filter(c => c.model.includes('whisper')).length === 1, [j, aiCalls.length]);
aiMode = 'icelandic'; aiCalls.length = 0;
[code, j] = await call('/listen', { rid: 'rL', audio: 'A'.repeat(2000), lang: 'te' }, 'pat1');
ok('language chosen by the user → heard once in that language', aiCalls.filter(c => c.model.includes('whisper')).length === 1 && aiCalls[0].input.language === 'te', aiCalls.map(c => c.input.language));
aiMode = 'ok';
ok('only people in the live consultation', (await call('/listen', { rid: 'rL', audio: 'A'.repeat(2000) }, 'other'))[0] === 403);

// ---- payment reminders (cron) ----
const tok = 'gtok';
const istNow = new Date(T + 330 * 60000); // India time
const slot = mins => { const d = new Date(T + mins * 60000 + 330 * 60000); return [d.toISOString().slice(0, 10), d.toISOString().slice(11, 16)]; };
const [d60, t60] = slot(55), [d10, t10] = slot(8), [dF, tF] = slot(300);
db.set('requests/p1', { id: 'p1', doctorId: 'doc1', patientId: 'pat1', status: 'accepted', slotDate: d60, slotTime: t60, tz: -330 });
db.set('requests/p2', { id: 'p2', doctorId: 'doc1', patientId: 'pat1', status: 'waiting', slotDate: d10, slotTime: t10 }); // no tz → India time
db.set('requests/p3', { id: 'p3', doctorId: 'doc1', patientId: 'pat1', status: 'accepted', slotDate: d10, slotTime: t10, tz: -330, paid: { inr: 300 } });
db.set('requests/p4', { id: 'p4', doctorId: 'doc1', patientId: 'pat1', status: 'accepted', slotDate: d10, slotTime: t10, tz: -330, feeWaived: { at: 1 } });
db.set('requests/p5', { id: 'p5', doctorId: 'doc1', patientId: 'pat1', status: 'accepted', slotDate: dF, slotTime: tF, tz: -330 });
fcm.length = 0;
let n = await W.runPayReminders(env, PID, tok, T);
const bodies = fcm.map(m => m.data.body);
ok('pay reminder 1 hour before, and 10 minutes before', n === 2 && bodies.some(b => b.includes('is today at') && b.includes('₹300')) && bodies.some(b => b.startsWith('Your consultation with Dr. Ananya Rao is at')), bodies);
ok('no reminder when paid, free or far away', !fcm.some(m => /p3|p4|p5/.test(m.data.tag)), fcm.map(m => m.data.tag));
ok('reminders are urgent and open the consultation', fcm.every(m => m.data.kind === 'urgent' && m.data.url.startsWith('./?go=consult&id=p')));
fcm.length = 0;
n = await W.runPayReminders(env, PID, tok, T + 60000);
ok('each reminder is sent only once', n === 0 && fcm.length === 0);
ok('no PayPal on the worker → no pay reminders', (await W.runPayReminders({ ...env, PAYPAL_CLIENT_ID: '' }, PID, tok, T)) === 0);
// ---- faster alerts ----
const push = async (body, uid) => { const r = await worker.fetch(new Request('https://w.dev/push', { method: 'POST', headers: { Origin: 'https://healvio.web.app', 'content-type': 'application/json', authorization: 'Bearer ' + await idToken(uid) }, body: JSON.stringify(body) }), env, { waitUntil() {} }); return r.json(); };
db.set('pushTokens/doc1', { tokens: ['tokD'] });
fcm.length = 0;
// the phone sends the push request at the same moment it saves the alert: the alert arrives 400 ms later
setTimeout(() => db.set('notifications/nfast', { id: 'nfast', to: 'doc1', text: 'Ravi paid your fee', ref: { view: 'consult', id: 'r1' }, kind: 'info', at: Date.now(), from: 'pat1', title: 'Payment received' }), 400);
let t0 = Date.now(), pr = await push({ id: 'nfast', to: 'doc1' }, 'pat1');
ok('alert sent even when the request arrives before the alert is saved', pr.sent === 1 && fcm.some(m => m.token === 'tokD' && m.data.body === 'Ravi paid your fee'), [pr, Date.now() - t0]);
ok('title from the alert is shown', fcm.some(m => m.data.title === 'Healvio · Payment received'));
fcm.length = 0;
db.set('notifications/nhint', { id: 'nhint', to: 'pat1', text: 'real target', at: Date.now(), from: 'doc1' });
pr = await push({ id: 'nhint', to: 'doc1' }, 'doc1');
ok('a wrong "to" in the request cannot redirect the alert (the saved alert decides)', pr.sent === 1 && fcm.every(m => m.token === 'tokP'), fcm.map(m => m.token));
fcm.length = 0;
t0 = Date.now(); pr = await push({ id: 'nmissing', to: 'doc1' }, 'pat1');
ok('an alert that was never saved is not sent', pr.sent === 0 && fcm.length === 0, [pr, Date.now() - t0]);
// ---- reminders every minute, payments every 5 minutes ----
db.delete('system/cron');
let c1 = await W.runReminders(env, T); const s1 = db.get('system/cron');
let c2 = await W.runReminders(env, T + 60000); const s2 = db.get('system/cron');
ok('cron every minute: the gap is recorded (1 minute)', s2.gap === 60000, s2);
ok('payment reminders checked at most every 5 minutes', s1.payAt === T && s2.payAt === T);
await W.runReminders(env, T + 300000);
ok('…and again after 5 minutes', db.get('system/cron').payAt === T + 300000);
console.log('\n' + results.filter(Boolean).length + '/' + results.length + ' passed');
