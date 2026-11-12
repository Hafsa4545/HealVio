import re, json, subprocess, time
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8103'))
KEY = 'BKrC6jePyiPug3DIb-xAkQ8G0MuJuvwQq6-jZQesTtZC5s908ulwrRZqFUyyiZPDiAuRyMGOOfDsKEygQppBETY'
CFG = CFG.replace('VAPID-KEY', KEY)
answers, push_log = [], []
def push_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    push_log.append(json.loads(route.request.post_data))
    j(route, answers.pop(0) if answers else {'sent': 1, 'phones': 1})

UNIT = r"""(() => {
  const out = {};
  const T = today();
  // a working day (not Sunday) in the future, and the days after it
  let d1 = addDays(T, 1); while (isSunday(d1) || isSunday(addDays(d1, 1)) || isSunday(addDays(d1, 2))) d1 = addDays(d1, 1);
  const d2 = addDays(d1, 1), d3 = addDays(d1, 2);
  const doc = (av, reuse, extra) => ({ id: 'x', doc: Object.assign({ avail: av, reuse }, extra || {}) });
  const A = { [d1]: { start: '10:00', every: 20, count: 10 } };
  out.example = allSlots(doc(A, true), d1).map(t12).join(', ');
  out.p1 = dayPlan(doc(A, true), d1).how;
  const p2 = dayPlan(doc(A, true), d2); out.copied = [p2.how, p2.from === d1, allSlots(doc(A, true), d2).length, p2.start, p2.every];
  out.reuseOff = [dayPlan(doc(A, false), d2), allSlots(doc(A, false), d2).length];
  const own = { [d1]: { start: '10:00', every: 20, count: 10 }, [d2]: { start: '15:00', every: 30, count: 4 } };
  out.ownKept = [dayPlan(doc(own, true), d2).how, allSlots(doc(own, true), d2).join(','), dayPlan(doc(own, true), d3).from === d2];
  // Sunday: off by default even with reuse; Monday copies Saturday
  let sat = addDays(T, 1); while (new Date(sat + 'T00:00').getDay() !== 6) sat = addDays(sat, 1);
  const sun = addDays(sat, 1), mon = addDays(sat, 2);
  const S = { [sat]: { start: '09:00', every: 15, count: 8 } };
  out.sunday = [dayPlan(doc(S, true), sun).off, allSlots(doc(S, true), sun).length];
  const pm = dayPlan(doc(S, true), mon); out.monday = [pm.how, pm.from === sat, allSlots(doc(S, true), mon).length];
  out.sundayManual = allSlots(doc({ [sun]: { start: '11:00', every: 30, count: 2 } }, true), sun).join(',');
  // a day off set by the doctor is not copied, the day after copies the last working day
  const off = { [d1]: { start: '10:00', every: 20, count: 3 }, [d2]: { off: true } };
  out.offDay = [allSlots(doc(off, true), d2).length, dayPlan(doc(off, true), d3).from === d1];
  // nothing set at all → no slots (new doctor), earlier weekly timings still work for older doctors
  out.none = [dayPlan(doc({}, true), d1), allSlots(doc({}, true), d1).length];
  const dow = new Date(d1 + 'T00:00').getDay();
  const W = doc(undefined, undefined, { days: [dow], start: '09:00', end: '10:00', slot: 15 });
  out.weekly = [dayPlan(W, d1).how, allSlots(W, d1).join(',')];
  out.weeklyOffWhenReuseOff = allSlots(doc({}, false, { days: [dow], start: '09:00', end: '10:00', slot: 15 }), d1).length;
  out.midnight = allSlots(doc({ [d1]: { start: '23:00', every: 30, count: 5 } }, true), d1).join(',');
  out.bad = [dayPlan(doc({ [d1]: { start: '10:00', every: 20, count: 0 } }, true), d1), dayPlan(doc({ [d1]: { start: 'x', every: 20, count: 3 } }, true), d1)];
  out.d1 = d1;
  return out;
})()"""
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
        ok('10:00 AM, 20 min, 10 slots → exactly the 10 times from your example', u['example'] == '10:00 AM, 10:20 AM, 10:40 AM, 11:00 AM, 11:20 AM, 11:40 AM, 12:00 PM, 12:20 PM, 12:40 PM, 1:00 PM', u['example'])
        ok('a day the doctor set is marked "set by you"', u['p1'] == 'manual')
        ok('reuse ON: next day copies start, minutes and number of slots, and says where it came from', u['copied'] == ['copied', True, 10, '10:00', 20], u['copied'])
        ok('reuse OFF: a day not set has no slots', u['reuseOff'] == [None, 0], u['reuseOff'])
        ok('a day the doctor set is never overwritten by copying', u['ownKept'][0] == 'manual' and u['ownKept'][1] == '15:00,15:30,16:00,16:30' and u['ownKept'][2] is True, u['ownKept'])
        ok('Sunday is a day off by default (even with reuse ON)', u['sunday'] == [True, 0], u['sunday'])
        ok('Monday copies Saturday (Sunday skipped)', u['monday'] == ['copied', True, 8], u['monday'])
        ok('the doctor can still choose to work on a Sunday', u['sundayManual'] == '11:00,11:30', u['sundayManual'])
        ok('a day off set by the doctor has no slots and is not copied', u['offDay'] == [0, True], u['offDay'])
        ok('nothing set at all (new doctor) → no slots', u['none'] == [None, 0], u['none'])
        ok('doctors with the old weekly timings keep working until they set a day', u['weekly'][0] == 'weekly' and u['weekly'][1] == '09:00,09:15,09:30,09:45', u['weekly'])
        ok('…but not when they chose to set every day themselves', u['weeklyOffWhenReuseOff'] == 0)
        ok('slots never go past midnight', u['midnight'] == '23:00,23:30', u['midnight'])
        ok('wrong values give no slots (no crash)', u['bad'] == [None, None], u['bad'])
        d1 = u['d1']
        # ---- doctor screen ----
        D.evaluate("root('dQueue')"); W(D, 500)
        t = D.evaluate("document.body.innerText")
        ok("doctor goes straight to the dashboard and sees Today's availability", "Today's availability" in t and 'Plan other days' in t, t[:400])
        D.evaluate("ACT.sheet({ k: 'dayAvail', id: %s })" % json.dumps(d1)); W(D, 400)
        D.fill('#av-start', '10:00'); D.select_option('#av-every', '20'); D.fill('#av-count', '10'); W(D, 400)
        st = D.evaluate("document.querySelector('.sheet').innerText")
        ok('preview shows 10 slots, 10:00 AM to 1:20 PM, before saving', '10 slots' in st and '10:00 AM to 1:20 PM' in st and '1:00 PM' in st, st[:600])
        D.click('button:has-text("Save")'); W(D, 1200)
        saved = D.evaluate("me().doc.avail[%s]" % json.dumps(d1))
        ok('saved for that day only', saved and saved['start'] == '10:00' and saved['every'] == 20 and saved['count'] == 10, saved)
        W(P, 800)
        pslots = P.evaluate("allSlots(Store.data.public[%s], %s).map(t12).join(', ')" % (json.dumps(DOC), json.dumps(d1)))
        ok('patients see those 10 times for that day', pslots.startswith('10:00 AM, 10:20 AM') and pslots.endswith('1:00 PM') and pslots.count(',') == 9, pslots)
        d2 = P.evaluate("addDays(%s, 1)" % json.dumps(d1))
        ok('patients see the next day copied (reuse is on by default)', P.evaluate("dayPlan(Store.data.public[%s], %s).how" % (json.dumps(DOC), json.dumps(d2))) == 'copied')
        # reuse off
        D.evaluate("state.sheet = null; root('dQueue')"); W(D, 300)
        D.click('.avcard input[type=checkbox]'); W(D, 1200)
        ok('doctor turns reuse off', D.evaluate("me().doc.reuse") is False)
        W(P, 800)
        ok('patients then see no slots on a day the doctor did not set', P.evaluate("allSlots(Store.data.public[%s], %s).length" % (json.dumps(DOC), json.dumps(d2))) == 0)
        D.click('.avcard input[type=checkbox]'); W(D, 1000)
        # day off + remove setting
        D.evaluate("ACT.sheet({ k: 'dayAvail', id: %s })" % json.dumps(d1)); W(D, 400)
        D.click('#av-off'); W(D, 300); D.click('button:has-text("Save")'); W(D, 1000)
        ok('a date can be marked as a day off', D.evaluate("me().doc.avail[%s].off" % json.dumps(d1)) is True and P.evaluate("allSlots(Store.data.public[%s], %s).length" % (json.dumps(DOC), json.dumps(d1))) == 0)
        D.evaluate("ACT.sheet({ k: 'dayAvail', id: %s })" % json.dumps(d1)); W(D, 400)
        D.click('button:has-text("Remove my setting for this day")'); W(D, 1000)
        ok('the setting for a day can be removed', D.evaluate("!(%s in me().doc.avail)" % json.dumps(d1)))
        # booked patients keep their times
        D.evaluate("ACT.sheet({ k: 'dayAvail', id: %s })" % json.dumps(d1)); W(D, 300)
        ok('no "Timings & fee" weekly hours left to fill in', 'Available days' not in D.evaluate("document.body.innerText"))
        D.evaluate("state.sheet = null; ACT.sheet({ k: 'timings' })"); W(D, 400)
        tt = D.evaluate("document.querySelector('.sheet') ? document.querySelector('.sheet').innerText : ''")
        ok('Fee & details sheet has no weekly hours, explains daily timings', 'Available days' not in tt and 'Fee & details' in tt and "Today's availability" in tt, tt[:300])
        D.evaluate("state.form.tm.fee = 450"); D.click('.sheet button:has-text("Save")'); W(D, 800)
        ok('fee still saves', D.evaluate("me().doc.fee") == 450)
        ok('doctor sign-up form shows without weekly timings', 'After approval you set your timings for each day' in D.evaluate("(() => { state.form.ob = null; return VIEWS.dOnboard().body; })()"))
        D.evaluate("state.sheet = null; state.form.ob = null; root('dQueue')"); W(D, 500)
        D.screenshot(path='/tmp/av_card.png')
        D.evaluate("ACT.sheet({ k: 'dayAvail', id: today() })"); W(D, 400)
        D.fill('#av-start', '10:00'); D.select_option('#av-every', '20'); D.fill('#av-count', '10'); W(D, 400)
        D.screenshot(path='/tmp/av_sheet.png')
        D.evaluate("state.sheet = null; render()"); W(D, 200)
        P.evaluate("go('pDoctor', { id: %s })" % json.dumps(DOC)); W(P, 700)
        P.evaluate("document.querySelector('.avweek') && document.querySelector('.avweek').scrollIntoView()"); W(P, 300)
        P.screenshot(path='/tmp/av_patient.png')
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
