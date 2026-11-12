import re, json, subprocess, time
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8104'))
KEY = 'BKrC6jePyiPug3DIb-xAkQ8G0MuJuvwQq6-jZQesTtZC5s908ulwrRZqFUyyiZPDiAuRyMGOOfDsKEygQppBETY'
CFG = CFG.replace('VAPID-KEY', KEY)
SEED['requests/r1'] = {**SEED['requests/r1'], 'status': 'completed', 'endedAt': T, 'rateSkipped': True}
push_log = []
def push_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    push_log.append(json.loads(route.request.post_data))
    j(route, {'sent': 1, 'phones': 1})
def notes(p, prefix):
    return p.evaluate("(pre) => [...globalThis.__fsStore.entries()].filter(([k]) => k.startsWith('notifications/' + pre)).map(([k, v]) => v)", prefix)
def req(p, rid): return p.evaluate("(id) => globalThis.__fsStore.get('requests/' + id) || {}", rid)
def txt(p, sel='body'): return p.evaluate("(s) => { const e = document.querySelector(s); return e ? e.innerText : ''; }", sel)

# the same scenario as the server test (wtest11): the app and the server must agree
UNIT = r"""(() => {
  const d = today(), at = hm => new Date(d + 'T' + hm).getTime();
  const live = { id: 'rA', doctorId: 'doc1', status: 'live', slotDate: d, slotTime: '10:00', slotLen: 20, startedAt: at('09:59') };
  const mk = (id, t, extra) => Object.assign({ id, doctorId: 'doc1', status: 'accepted', slotDate: d, slotTime: t, slotLen: 20 }, extra || {});
  const list = [live, mk('rB', '10:20'), mk('rC', '10:40', { status: 'waiting' }), mk('rD', '11:00'), mk('rE', '12:20'), mk('rF', '10:20', { doctorId: 'doc2' }), mk('rG', '09:40', { status: 'completed' }), mk('rH', '10:20', { slotDate: addDays(d, 1) })];
  const plan = delayPlan(live, list, at('10:20')).map(p => p.r.id + '@' + p.to);
  const told = delayPlan(live, list.map(x => x.id === 'rC' ? Object.assign({}, x, { delayFor: bookKey(x) }) : x), at('10:20')).map(p => p.r.id + '@' + p.to);
  return { plan, told, mm: [mmss(0), mmss(61000), mmss(20 * 60000), mmss(3725000)], left: [timerLeft(1000000, 1000000 - 90000), timerLeft(1000000, 1000000 + 61000), timerLeft(1000000, 1000000 + 11 * 60000)] };
})()"""
SETUP = r"""([DOC, PAT]) => {
  const t = Date.now(), d = today(), hm = ms => fromMin(new Date(ms).getHours() * 60 + new Date(ms).getMinutes());
  const S = t - 21 * 60000; // started 21 minutes ago, 20-minute slot → 1 minute over time
  const base = { doctorId: DOC, mode: 'chat', type: 'normal', problem: 'Check-up', createdAt: t - 3600e3, slotDate: d, slotLen: 20, tz: new Date().getTimezoneOffset() };
  const docs = {
    'requests/rL': { ...base, id: 'rL', patientId: 'gmeena', patient: { name: 'Meena Iyer' }, status: 'live', slotTime: hm(S), startedAt: S },
    'requests/rB': { ...base, id: 'rB', patientId: PAT, patient: { name: 'Ravi Kumar' }, status: 'accepted', slotTime: hm(S + 20 * 60000), problem: 'Knee pain', paid: { by: 'paypal', inr: 300, at: t } },
    'requests/rC': { ...base, id: 'rC', patientId: 'gyash', patient: { name: 'Yash' }, status: 'waiting', queueNo: 1, slotTime: hm(S + 40 * 60000), paid: { by: 'paypal', inr: 300, at: t } },
    'requests/rE': { ...base, id: 'rE', patientId: 'gzed', patient: { name: 'Zed' }, status: 'accepted', slotTime: hm(S + 160 * 60000) },
  };
  const bc = new BroadcastChannel('fs-sync');
  for (const [k, v] of Object.entries(docs)) { globalThis.__fsStore.set(k, v); bc.postMessage({ t: 'w', path: k, d: v }); }
  globalThis.__fsFire();
  return { rB: docs['requests/rB'].slotTime, rC: docs['requests/rC'].slotTime, rE: docs['requests/rE'].slotTime, exB: hm(S + 30 * 60000), exC: hm(S + 50 * 60000) };
}"""
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, geolocation=HOME, permissions=['geolocation', 'notifications'])
        def mk(f):
            body = open(f'fs_{f}.js').read()
            return lambda r: r.fulfill(status=200, content_type='application/javascript', headers={'Access-Control-Allow-Origin': '*'}, body=body)
        ctx.route(re.compile(r'https://fonts\..*'), lambda r: r.abort())
        for mod, f in [('app', 'app'), ('firestore', 'firestore_shared'), ('auth', 'auth'), ('messaging', 'messaging')]:
            ctx.route(f'https://www.gstatic.com/firebasejs/{V}/firebase-{mod}.js', mk(f))
        ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
        ctx.route(re.compile(r'https://w\.healvio\.test/status(\?.*)?$'), lambda r: j(r, status))
        ctx.route('https://w.healvio.test/push', push_route)
        ctx.route('https://w.healvio.test/ice', lambda r: j(r, {'iceServers': []}))
        D = ctx.new_page(); D.on('pageerror', lambda e: errs.append(('D', str(e)))); D.goto(URL); W(D, 1400)
        P = ctx.new_page(); P.on('pageerror', lambda e: errs.append(('P', str(e)))); P.goto(URL); W(P, 1400)
        seed(D); W(D, 400)
        for p, email, name in [(D, DOC_E, 'Ananya Rao'), (P, PAT_E, 'Ravi Kumar')]:
            p.evaluate(f"globalThis.__googleEmail={json.dumps(email)}; globalThis.__googleName={json.dumps(name)}")
            p.click('button:has-text("Continue with Google")'); W(p, 1300)
        for p in (P, D): p.evaluate("state.confirm = null; state.modal = null; state.sheet = null; render()"); W(p, 150)
        u = P.evaluate(UNIT)
        ok('app works out the same delays as the server: 10:30, 10:50, 11:10; gap stops it; others untouched', u['plan'] == ['rB@10:30', 'rC@10:50', 'rD@11:10'], u['plan'])
        ok('a patient already told is never told again (the chain still counts them)', u['told'] == ['rB@10:30', 'rD@11:10'], u['told'])
        ok('clock text: 0:00, 1:01, 20:00, 1:02:05', u['mm'] == ['0:00', '1:01', '20:00', '1:02:05'], u['mm'])
        ok('remaining / over text', u['left'] == ['1:30 left', 'Time over · +1:01', 'Over time · +11:00'], u['left'])

        tm = D.evaluate(SETUP, [DOC, PAT]); W(D, 800); W(P, 400)
        D.evaluate("root('dQueue')"); W(D, 500)
        D.evaluate("CT.check(true)"); W(D, 2500)
        tup1 = notes(D, 'tup1-rL')
        ok('time up: the doctor gets the "time is up" reminder (from the phone, the server does the same for locked phones)', len(tup1) == 1 and tup1[0]['to'] == DOC and 'Meena Iyer' in tup1[0]['text'] and '10 extra minutes' in tup1[0]['text'] and tup1[0].get('title') == 'Consultation time is up', tup1)
        rl = req(D, 'rL')
        ok('consultation marked: reminder 1 sent, delay notices sent', rl.get('tup') == 1 and rl.get('dlyAt'), {k: rl.get(k) for k in ('tup', 'dlyAt', 'status')})
        dB, dC, dE = notes(D, 'dly-rB'), notes(D, 'dly-rC'), notes(D, 'dly-rE')
        ok('next patients told once: about 10 minutes late with booked and expected time', len(dB) == 1 and len(dC) == 1 and 'running about 10 minutes late' in dB[0]['text'] and P.evaluate("t12(%s)" % json.dumps(tm['exB'])) in dB[0]['text'] and P.evaluate("t12(%s)" % json.dumps(tm['rB'])) in dB[0]['text'], (dB, tm))
        ok('a patient after a free gap is not told', len(dE) == 0)
        rb = req(D, 'rB')
        ok('booking keeps its booked time; the expected time is saved next to it', rb.get('slotTime') == tm['rB'] and rb.get('delayTo') == tm['exB'] and rb.get('delayFor') and rb.get('delayBy') == 'rL', {k: rb.get(k) for k in ('slotTime', 'delayTo', 'delayFor', 'delayBy')})
        ok("patients' phones are rung for the delay notice", any(x.get('to') == PAT and str(x.get('id', '')).startswith('dly-rB') for x in push_log) and any(x.get('to') == 'gyash' for x in push_log), push_log[-4:])
        n0 = len(push_log)
        D.evaluate("CT.check(true)"); W(D, 2000)
        ok('checking again: nothing is sent twice', len(push_log) == n0 and len(notes(D, 'tup1-rL')) == 1 and len(notes(D, 'dly-rB')) == 1, push_log[n0:])
        # patient sees it
        W(P, 600)
        P.evaluate("go('consult', { id: 'rB' })"); W(P, 600)
        pt = txt(P, 'main')
        ok('patient sees: running about 10 minutes late, booked and expected time', 'running about 10 minutes late' in pt and ('Booked: ' + P.evaluate("t12(%s)" % json.dumps(tm['rB']))) in pt and ('Expected: about ' + P.evaluate("t12(%s)" % json.dumps(tm['exB']))) in pt, pt[:500])
        ok('patient got the delay alert in the app', P.evaluate("Object.values(Store.data.notifications).some(n => n.id.startsWith('dly-rB') && n.title === 'Consultation delayed')"))
        P.screenshot(path='/tmp/tm_patient_delay.png')
        # doctor's room: timer + banner
        D.evaluate("go('room', { id: 'rL' })"); W(D, 900)
        bar = txt(D, '.ctimer')
        ok('doctor room: timer shows time passed, "Time over" and the reminder', D.evaluate("document.querySelector('.ctimer').classList.contains('grace')") and re.search(r'\b21:\d\d\b', bar) and 'Time over · +1:' in bar and 'Time is up' in bar and '10 extra minutes' in bar, bar)
        ok('doctor room: says how many next patients were told', '2 next patients were told' in bar, bar)
        e1 = D.evaluate("document.querySelector('[data-tk=el]').textContent"); W(D, 2200); e2 = D.evaluate("document.querySelector('[data-tk=el]').textContent")
        ok('the clock moves every second', e1 != e2, (e1, e2))
        D.click('#composer'); D.keyboard.type('Please continue the tablets'); W(D, 3000)
        ok('typing is not disturbed by the clock', D.evaluate("document.activeElement && document.activeElement.id === 'composer' && document.activeElement.value === 'Please continue the tablets'"))
        D.screenshot(path='/tmp/tm_doctor_grace.png')
        # refresh keeps the clock
        D.reload(); W(D, 2000)
        D.evaluate(f"globalThis.__googleEmail={json.dumps(DOC_E)}; globalThis.__googleName='Ananya Rao'")
        if D.locator('button:has-text("Continue with Google")').count(): D.click('button:has-text("Continue with Google")'); W(D, 1500)
        D.evaluate("state.confirm = null; state.modal = null; state.sheet = null; go('room', { id: 'rL' })"); W(D, 1200)
        bar2 = txt(D, '.ctimer')
        ok('after refresh the clock carries on (not reset)', re.search(r'\b2[1-3]:\d\d\b', bar2) and 'Time over' in bar2, bar2)
        # 10 more minutes: stronger reminder, never ends by itself
        server_write(D, 'requests/rL', {'startedAt': D.evaluate("Date.now()") - 31 * 60000}); W(D, 700)
        D.evaluate("CT.check(true)"); W(D, 2200)
        tup2 = notes(D, 'tup2-rL')
        ok('10 extra minutes over: stronger (urgent) reminder to the doctor', len(tup2) == 1 and tup2[0]['kind'] == 'urgent' and 'will not end by itself' in tup2[0]['text'] and req(D, 'rL').get('tup') == 2, tup2)
        bar3 = txt(D, '.ctimer')
        ok('room shows "Over time" in red and asks the doctor to end when done', D.evaluate("document.querySelector('.ctimer').classList.contains('late')") and 'Over time · +11:' in bar3 and 'Please end the consultation' in bar3, bar3)
        ok('the consultation is still going (never ended automatically)', req(D, 'rL').get('status') == 'live')
        ok('no new delay notices for the same patients', len(notes(D, 'dly-rB')) == 1 and len(notes(D, 'dly-rC')) == 1)
        D.screenshot(path='/tmp/tm_doctor_late.png')
        # the server sent the reminder first → the phone does not send it again
        server_write(D, 'requests/rS', {'id': 'rS', 'doctorId': DOC, 'patientId': 'gsam', 'patient': {'name': 'Sam'}, 'status': 'live', 'mode': 'chat', 'type': 'normal', 'problem': 'x', 'createdAt': T, 'slotDate': D.evaluate("today()"), 'slotTime': '00:01', 'slotLen': 15, 'startedAt': D.evaluate("Date.now()") - 16 * 60000, 'dlyAt': 1})
        server_write(D, 'notifications/tup1-rS', {'id': 'tup1-rS', 'to': DOC, 'from': 'system', 'text': 'The 15-minute consultation time with Sam is over.', 'kind': 'info', 'at': D.evaluate("Date.now()"), 'read': False, 'ref': {'view': 'room', 'id': 'rS'}})
        W(D, 500); D.evaluate("CT.check(true)"); W(D, 2000)
        ok('already sent by the server: the phone does not send it again, just marks it', notes(D, 'tup1-rS')[0]['from'] == 'system' and req(D, 'rS').get('tup') == 1, (notes(D, 'tup1-rS'), req(D, 'rS').get('tup')))
        server_write(D, 'requests/rS', {'status': 'completed', 'endedAt': D.evaluate("Date.now()")}); W(D, 400)
        # ---- update 4: end → next patient "be ready" ----
        D.evaluate("go('room', { id: 'rL' })"); W(D, 500)
        n0 = len(push_log)
        D.click('button:has-text("End consult")'); D.click('.modal button:has-text("End consultation")'); W(D, 2200)
        nx = notes(D, 'nxt-rB')
        ok('consultation ended: the next patient is told "please be ready"', len(nx) == 1 and nx[0]['to'] == PAT and 'finished the previous consultation' in nx[0]['text'] and 'Please be ready' in nx[0]['text'] and nx[0].get('title') == 'Please be ready', nx)
        ok('their phone is rung', any(x.get('to') == PAT and str(x.get('id', '')).startswith('nxt-rB') for x in push_log[n0:]), push_log[n0:])
        ok('nobody else is told to be ready', len(notes(D, 'nxt-rC')) == 0 and len(notes(D, 'nxt-rE')) == 0)
        dt = txt(D, 'main')
        ok('doctor sees who is next right after ending', 'Next patient' in dt and 'Up next: Ravi Kumar' in dt and "I'm ready" in dt and 'Told to be ready' in dt, dt[-700:])
        W(P, 700); P.evaluate("render()"); W(P, 300)
        pt = txt(P, 'main')
        ok('patient now sees "Please be ready — you\'re next" (newest message wins)', "Please be ready — you're next" in pt and 'running about 10 minutes late' not in pt, pt[:400])
        # doctor "I'm ready"
        D.evaluate("root('dQueue')"); W(D, 600)
        qt = txt(D, 'main')
        ok('doctor home shows "Up next" with I\'m ready and Start', 'Up next: Ravi Kumar' in qt and "I'm ready" in qt, qt[:500])
        D.screenshot(path='/tmp/tm_doctor_upnext.png')
        n0 = len(push_log)
        D.click('.nownext button:has-text("I\'m ready")'); W(D, 1800)
        rd = notes(D, 'rdy-rB')
        ok('"I\'m ready" tells the patient: your doctor is ready', len(rd) == 1 and 'is ready for you now' in rd[0]['text'] and rd[0]['kind'] == 'urgent' and rd[0].get('title') == 'Your doctor is ready' and any(str(x.get('id', '')).startswith('rdy-rB') for x in push_log[n0:]), rd)
        D.click('.nownext button:has-text("I\'m ready")'); W(D, 1200)
        ok('tapping again at once does not send it twice', len(notes(D, 'rdy-rB')) == 1)
        W(P, 700); P.evaluate("render()"); W(P, 300)
        pt = txt(P, 'main')
        ok('patient sees "Your doctor is ready for you"', 'Your doctor is ready for you' in pt, pt[:400])
        P.screenshot(path='/tmp/tm_patient_ready.png')
        ok('doctor sees what the patient was told', "Told you're ready" in txt(D, 'main'), txt(D, 'main')[:600])
        # start: a third, different message
        n0 = len(push_log)
        D.click('.nownext button:has-text("Start")'); W(D, 2200)
        W(P, 800)
        st_note = P.evaluate("Object.values(Store.data.notifications).filter(n => n.title === 'Consultation started').map(n => n.text)")
        ok('consultation started: its own message, different from "be ready" and "doctor ready"', len(st_note) == 1 and 'has started your consultation' in st_note[0] and 'is ready for you now' not in st_note[0], st_note)
        ok('three different messages reached the patient', P.evaluate("['nxt-rB', 'rdy-rB'].every(p => Object.values(Store.data.notifications).some(n => n.id.startsWith(p)))"))
        rb = req(D, 'rB')
        ok('the timer length is saved at the start (both phones and the server use it)', rb.get('slotLen') == 20 and rb.get('status') == 'live' and rb.get('startedAt'), {k: rb.get(k) for k in ('slotLen', 'status')})
        P.evaluate("go('room', { id: 'rB' })"); W(P, 900)
        pb = txt(P, '.ctimer')
        ok('patient sees the timer too: time passed and time left', re.search(r'\b0:0\d\b', pb) and re.search(r'\b(19|20):\d\d left\b', pb) and 'of 20 min' in pb, pb)
        P.screenshot(path='/tmp/tm_patient_room.png')
        # early finish: no time-up reminder, the next patient is told to be ready
        D.evaluate("go('room', { id: 'rB' })"); W(D, 500)
        D.click('button:has-text("End consult")'); D.click('.modal button:has-text("End consultation")'); W(D, 2200)
        ok('finished early: no "time is up" reminder and no delay notices', len(notes(D, 'tup1-rB')) == 0 and len(notes(D, 'dly-rE')) == 0)
        ok('finished early: the next patient is told to be ready right away', len(notes(D, 'nxt-rC')) == 1, notes(D, 'nxt-rC'))
        D.evaluate("root('dQueue'); state.tab.dq = 'waiting'; render()"); W(D, 500)
        ok("doctor's list shows what that patient was told", 'Told: about 10 min late' in txt(D, 'main') and 'Told to be ready' in txt(D, 'main'), txt(D, 'main')[-500:])
        ok('a patient whose slot is hours away is not told to be ready', len(notes(D, 'nxt-rE')) == 0)
        D.evaluate("state.tab.dq = 'requests'; render()")
        bad = [x for x in D.evaluate('globalThis.__denied') + P.evaluate('globalThis.__denied') if not x.startswith('listen') and 'notifications/tup1-rS' not in x]
        ok('no refused saves (except the expected "already sent by the server")', not bad, bad)
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
