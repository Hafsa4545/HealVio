// Phone pop-ups in the patient's language (service worker)
import fs from 'fs';
const L = {}; let pass = 0, total = 0;
const ok = (n, c, x = '') => { total++; if (c) pass++; console.log((c ? 'PASS ' : 'FAIL ') + n, x === '' ? '' : '| ' + JSON.stringify(x)); };
// build the language pack exactly like the app does (same code, taken from the built app)
const html = fs.readFileSync('/home/claude/healvio-app/index.html', 'utf8');
const a = html.indexOf('const NOTE_TPL = '), b = html.indexOf('\nconst isChatNote');
const consts = new Function(html.slice(a, b) + '\nreturn { NOTE_TPL, NOTE_WORDS, NOTE_SLOT, NOTE_MD };')();
const ps = html.indexOf('  notePats() {'), pe = html.indexOf('\n  },\n  // a date', ps);
const I = new Function('NOTE_TPL', 'NOTE_SLOT', 'return { tpl: null, ' + html.slice(ps, pe) + '\n  } };')(consts.NOTE_TPL, consts.NOTE_SLOT);
const dict = JSON.parse(fs.readFileSync('/home/claude/healvio-app/i18n/te.json', 'utf8'));
const words = {}; consts.NOTE_WORDS.forEach(k => { if (dict[k]) words[k] = dict[k]; });
const loc = { Nov: 'నవం', Fri: 'శుక్ర' };
const packOn = { on: true, lang: 'Telugu', words, loc, tpl: I.notePats().filter(p => dict[p.key]).map(p => [p.src, p.types, dict[p.key], p.lit]) };
ok('the app sends every alert pattern to the phone', packOn.tpl.length === consts.NOTE_TPL.length, [packOn.tpl.length, consts.NOTE_TPL.length]);

let pack = packOn, visible = false, shown = [], deleted = [], keys = [];
const caches = {
  open: async name => ({ match: async url => name === 'healvio-lang' && pack && url === 'https://healvio.web.app/__lang' ? { json: async () => JSON.parse(JSON.stringify(pack)) } : undefined, put: async () => {}, addAll: async () => {} }),
  keys: async () => keys, delete: async k => { deleted.push(k); return true; }, match: async () => undefined
};
const self = { addEventListener: (t, f) => (L[t] = f), registration: { scope: 'https://healvio.web.app/', showNotification: async (t, o) => { shown.push({ t, o }); } },
  clients: { matchAll: async () => (visible ? [{ visibilityState: 'visible' }] : []), claim: async () => {} }, location: { origin: 'https://healvio.web.app' }, skipWaiting() {} };
new Function('self', 'caches', fs.readFileSync('/home/claude/healvio-app/sw.js', 'utf8'))(self, caches);
const push = async data => { shown = []; let p; L.push({ data: { json: () => ({ data }) }, waitUntil: x => (p = x) }); await p; return shown[0] || null; };
const te = s => /[ఀ-౿]/.test(s || '');

let n = await push({ kind: 'alert', title: 'Healvio · Request accepted', url: './?go=consult&id=r1',
  body: '✅ Dr. Ananya Rao accepted your request. Your slot: Fri, 14 Nov, 10:30 AM. Please pay the ₹500 fee in the app to confirm it. The consultation starts after payment.' });
ok('pop-up title in Telugu', n && n.t === 'Healvio · ' + dict['Request accepted'], n && n.t);
ok('pop-up text in Telugu, both sentences', n && te(n.o.body) && !/accepted|Please pay/.test(n.o.body), n && n.o.body);
ok('doctor name, price and time stay as written; the date is in Telugu', n && n.o.body.includes('Dr. Ananya Rao') && n.o.body.includes('₹500') && n.o.body.includes('10:30 AM') && n.o.body.includes('శుక్ర, 14 నవం'), n && n.o.body);
n = await push({ kind: 'urgent', title: '🔔 Healvio · Your doctor is ready', url: './?go=consult&id=r1', body: '🔔 Dr. Ananya Rao is ready for you now. Please open Healvio — your consultation will start in a moment. Please pay the ₹500 fee in the app first so the doctor can start.' });
ok('urgent pop-up: bell kept, title and text in Telugu', n && n.t === '🔔 Healvio · ' + dict['Your doctor is ready'] && te(n.o.body) && !/ready for you|first so/.test(n.o.body), n && [n.t, n.o.body]);
n = await push({ kind: 'alert', title: 'Healvio · Consultation', url: './?go=room&id=r1', body: 'Dr. Ananya Rao: Cheyadaniki ready ga undandi' });
ok('chat message stays exactly as the doctor typed it', n && n.o.body === 'Dr. Ananya Rao: Cheyadaniki ready ga undandi' && n.t === 'Healvio · ' + dict['Consultation'], n && [n.t, n.o.body]);
n = await push({ kind: 'alert', title: 'Healvio · Consultation started', url: './?go=room&id=r1', body: '▶️ Dr. Ananya Rao has started your consultation. Open the consult room to join.' });
ok('"consultation started" (opens the room) is still turned', n && te(n.o.body) && n.o.body.startsWith('▶️ Dr. Ananya Rao'), n && n.o.body);
n = await push({ kind: 'call', tag: 'call-c1', title: '📹 Incoming video call', url: './?go=room&id=r1', body: 'Dr. Ananya Rao is calling you. Tap to answer.' });
ok('incoming call: title, text and the Answer button in Telugu', n && n.t === '📹 ' + dict['Incoming video call'] && te(n.o.body) && n.o.actions[0].title === '✅ ' + dict['Answer'] && n.o.requireInteraction, n && [n.t, n.o.body, n.o.actions]);
n = await push({ kind: 'callend', tag: 'call-c1', title: '📞 Missed voice call', url: './?go=room&id=r1', body: 'Dr. Ananya Rao called you. Tap to open the consultation.' });
ok('missed call pop-up in Telugu', n && n.t === '📞 ' + dict['Missed voice call'] && te(n.o.body), n && [n.t, n.o.body]);
n = await push({ kind: 'alert', tag: 'med-1', title: '💊 Morning medicines', url: './?go=pHome', body: 'Paracetamol 650 1 tab (after food), ORS. Tap to mark them as taken.' });
ok('medicine reminder in Telugu, medicine names unchanged', n && n.t === '💊 ' + dict['Morning medicines'] && n.o.body.startsWith('Paracetamol 650 1 tab (after food), ORS') && te(n.o.body), n && [n.t, n.o.body]);
n = await push({ kind: 'urgent', title: '🔔 Healvio · Pay to confirm your consultation', url: './?go=consult&id=r1', body: 'Your consultation with Dr. Ananya Rao is today at 10:30 AM. Please pay the ₹500 fee in Healvio so the doctor can start on time.' });
ok('payment reminder from the worker in Telugu', n && n.t === '🔔 Healvio · ' + dict['Pay to confirm your consultation'] && te(n.o.body) && !/today at|Please pay/.test(n.o.body), n && [n.t, n.o.body]);
n = await push({ kind: 'alert', title: 'Healvio · Medicine order', url: './?go=order&id=o1', body: 'Sri Sai Medicals cancelled your medicine order: Out of stock. Your money was refunded to PayPal.' });
ok('reason typed by the store stays as typed, the rest in Telugu', n && n.o.body.includes('Sri Sai Medicals') && n.o.body.includes('Out of stock') && te(n.o.body) && !/refunded|cancelled/.test(n.o.body), n && n.o.body);
n = await push({ kind: 'alert', title: 'Healvio · Something new', url: './', body: 'A brand new kind of alert.' });
ok('an alert with no pattern stays in English (never broken)', n && n.o.body === 'A brand new kind of alert.' && n.t === 'Healvio · Something new', n && [n.t, n.o.body]);
pack = { on: false };
n = await push({ kind: 'alert', title: 'Healvio · Request accepted', url: './?go=consult&id=r1', body: '✅ Dr. Ananya Rao accepted your request. Your slot: Today, 10:30 AM.' });
ok('English chosen (or a doctor on this phone): pop-up stays English', n && n.t === 'Healvio · Request accepted' && n.o.body.startsWith('✅ Dr. Ananya Rao accepted'), n && [n.t, n.o.body]);
pack = null;
n = await push({ kind: 'call', title: '📹 Incoming video call', url: './?go=room&id=r1', body: 'Dr. Ananya Rao is calling you. Tap to answer.' });
ok('no language saved yet: English, Answer button unchanged', n && n.t === '📹 Incoming video call' && n.o.actions[0].title === '✅ Answer', n && [n.t, n.o.actions]);
pack = packOn; visible = true;
n = await push({ kind: 'alert', title: 'Healvio · Request accepted', url: './', body: 'x' });
ok('Healvio open on screen: no pop-up (the app shows it)', n === null);
visible = false;
pack = { ...packOn, names: { 'Dr. Ananya Rao': 'డా|| అనన్య రావు', 'Sri Sai Medicals': 'శ్రీ సాయి మెడికల్స్' } };
n = await push({ kind: 'alert', title: 'Healvio · Consultation', url: './?go=consult&id=r1', body: 'Your consultation with Dr. Ananya Rao is complete. Please rate your experience.' });
ok('doctor name in the pop-up as the app shows it (Telugu letters)', n && n.o.body.startsWith('డా|| అనన్య రావు తో') && !/Ananya/.test(n.o.body), n && n.o.body);
n = await push({ kind: 'alert', title: 'Healvio · Medicine order', url: './?go=order&id=o1', body: 'Sri Sai Medicals cancelled your medicine order: Out of stock. Your money was refunded to PayPal.' });
ok('store name in Telugu letters, the reason the store typed unchanged', n && n.o.body.startsWith('శ్రీ సాయి మెడికల్స్') && n.o.body.includes('Out of stock'), n && n.o.body);
n = await push({ kind: 'alert', title: 'Healvio · Consultation', url: './?go=room&id=r1', body: 'Dr. Ananya Rao: Cheyadaniki ready ga undandi' });
ok('chat pop-up: sender name in Telugu, message exactly as typed', n && n.o.body === 'డా|| అనన్య రావు: Cheyadaniki ready ga undandi', n && n.o.body);
n = await push({ kind: 'call', title: '📹 Incoming video call', url: './?go=room&id=r1', body: 'Dr. Ananya Rao is calling you. Tap to answer.' });
ok('incoming call pop-up with the doctor name in Telugu', n && n.o.body.startsWith('డా|| అనన్య రావు'), n && n.o.body);
n = await push({ kind: 'alert', title: 'Healvio · Consultation', url: './?go=room&id=r1', body: 'Dr. Unknown Person is ready for you now. Open the consult room to connect.' });
ok('a name not turned yet stays in English (never broken)', n && n.o.body.startsWith('Dr. Unknown Person ') && te(n.o.body), n && n.o.body);
n = await push({ kind: 'alert', title: 'Healvio · Consultation', url: './?go=room&id=r1', body: 'Dr. Ananya Rao is ready for you now. Open the consult room to connect.' });
ok('older "ready" alert that opens the consult room: in Telugu, with the doctor name', n && n.o.body.startsWith('డా|| అనన్య రావు') && te(n.o.body) && !/Open the consult/.test(n.o.body), n && n.o.body);
n = await push({ kind: 'alert', title: 'Healvio · Consultation', url: './?go=room&id=r1', body: 'Missed video call from Dr. Ananya Rao' });
ok('missed call pop-up in Telugu', n && te(n.o.body) && !/Missed/.test(n.o.body) && n.o.body.includes('డా|| అనన్య రావు'), n && n.o.body);
pack = packOn;
keys = ['healvio-v9', 'healvio-lang', 'healvio-v10']; deleted = [];
let ap; L.activate({ waitUntil: x => (ap = x) }); await ap.catch(() => {});
ok('after an update the saved language is kept (only old app files are cleared)', deleted.length === 1 && deleted[0] === 'healvio-v9', deleted);
console.log(`PASSED ${pass} / ${total}`);
