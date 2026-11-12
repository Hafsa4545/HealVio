import re, json, subprocess, time, sys
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8105'))
KEY = 'BKrC6jePyiPug3DIb-xAkQ8G0MuJuvwQq6-jZQesTtZC5s908ulwrRZqFUyyiZPDiAuRyMGOOfDsKEygQppBETY'
CFG = CFG.replace('VAPID-KEY', KEY)
def push_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    j(route, {'sent': 1, 'phones': 1})
EXTRA = r"""([DOC, PAT, ST]) => {
  const t = Date.now(), d = today(), base = { doctorId: DOC, patientId: PAT, patient: { name: 'Ravi Kumar', age: 30, phone: '9000000002' }, mode: 'video', type: 'normal', problem: 'Cough', createdAt: t - 3600e3, slotLen: 20 };
  const docs = {
    'requests/q1': { ...base, id: 'q1', status: 'requested', prefDate: d },
    'requests/q2': { ...base, id: 'q2', status: 'waiting', queueNo: 2, slotDate: d, slotTime: '23:40', waitAt: t },
    'requests/q3': { ...base, id: 'q3', status: 'accepted', slotDate: d, slotTime: '23:20', acceptedAt: t, delayAt: t, delayTo: '23:30', delayFor: d.replace(/-/g, '') + '2320', paid: { by: 'paypal', inr: 300, at: t } },
    'requests/q4': { ...base, id: 'q4', status: 'accepted', slotDate: d, slotTime: '23:00', acceptedAt: t, nextAt: t, nextFor: d.replace(/-/g, '') + '2300', readyAt: t + 1, readyFor: d.replace(/-/g, '') + '2300', paid: { by: 'paypal', inr: 300, at: t } },
    'requests/q5': { ...base, id: 'q5', status: 'live', slotDate: d, slotTime: '00:00', startedAt: t - 25 * 60000, paid: { by: 'paypal', inr: 300, at: t } },
    'requests/q6': { ...base, id: 'q6', status: 'rejected', closedAt: t, rejectReason: 'x' },
    'requests/q7': { ...base, id: 'q7', status: 'cancelled', closedAt: t },
    'orders/o2': { id: 'o2', rxId: 'rx1', storeId: ST, patientId: PAT, patient: { name: 'Ravi Kumar', phone: '9000000002' }, doctorName: 'Dr. Ananya Rao', storeName: 'Sri Ram Medicals', status: 'ready', total: 250, items: [{ name: 'Paracetamol 650', dose: '1 tab', available: true, price: 250 }], createdAt: t, updatedAt: t, respondedAt: t },
    'orders/o3': { id: 'o3', rxId: 'rx1', storeId: ST, patientId: PAT, patient: { name: 'Ravi Kumar', phone: '9000000002' }, doctorName: 'Dr. Ananya Rao', storeName: 'Sri Ram Medicals', status: 'out', mode: 'delivery', delivery: { address: 'x', lat: 17.44, lng: 78.44 }, total: 250, deliveryFee: 30, items: [{ name: 'Paracetamol 650', dose: '1 tab', available: true, price: 250 }], createdAt: t, updatedAt: t, paid: { by: 'paypal', inr: 280, at: t }, rider: { lat: 17.45, lng: 78.45, at: t }, riderName: 'Raju', outAt: t },
    'orders/o4': { id: 'o4', rxId: 'rx1', storeId: ST, patientId: PAT, patient: { name: 'Ravi Kumar', phone: '9000000002' }, doctorName: 'Dr. Ananya Rao', storeName: 'Sri Ram Medicals', status: 'delivered', mode: 'delivery', delivery: { address: 'x' }, total: 250, items: [{ name: 'Paracetamol 650', dose: '1 tab', available: true, price: 250 }], createdAt: t, updatedAt: t, deliveredAt: t },
  };
  const bc = new BroadcastChannel('fs-sync');
  for (const [k, v] of Object.entries(docs)) { globalThis.__fsStore.set(k, v); bc.postMessage({ t: 'w', path: k, d: v }); }
  globalThis.__fsFire();
}"""
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=1, is_mobile=True, has_touch=True, geolocation=HOME, permissions=['geolocation', 'notifications'])
        def mk(f):
            body = open(f'fs_{f}.js').read()
            return lambda r: r.fulfill(status=200, content_type='application/javascript', headers={'Access-Control-Allow-Origin': '*'}, body=body)
        ctx.route(re.compile(r'https://fonts\..*'), lambda r: r.abort())
        ctx.route(re.compile(r'https://unpkg\.com/leaflet.*\.js'), lambda r: r.fulfill(status=200, content_type='application/javascript', body=FAKE_L))
        for mod, f in [('app', 'app'), ('firestore', 'firestore_shared'), ('auth', 'auth'), ('messaging', 'messaging')]:
            ctx.route(f'https://www.gstatic.com/firebasejs/{V}/firebase-{mod}.js', mk(f))
        ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
        ctx.route(re.compile(r'https://w\.healvio\.test/status(\?.*)?$'), lambda r: j(r, status))
        ctx.route('https://w.healvio.test/push', push_route)
        P = ctx.new_page(); P.on('pageerror', lambda e: errs.append(('P', str(e)))); P.goto(URL); W(P, 1400)
        seed(P); W(P, 300)
        P.evaluate(EXTRA, [DOC, PAT, ST]); W(P, 300)
        P.evaluate(f"globalThis.__googleEmail={json.dumps(PAT_E)}; globalThis.__googleName='Ravi Kumar'")
        P.click('button:has-text("Continue with Google")'); W(P, 1500)
        P.evaluate("state.confirm = null; state.modal = null; state.sheet = null; I18N.collect = new Set(); I18N.start(); render()"); W(P, 300)
        def grab(js, ms=500):
            try: P.evaluate(js)
            except Exception as e: print('ERR', js[:80], str(e)[:150])
            W(P, ms); P.evaluate("I18N.walkAll()")
        steps = [
            "root('pHome')", "ACT.sheet({ k: 'filter' })", "state.sheet = null; ACT.sheet({ k: 'sort' })",
            "state.sheet = null; Finder.res = { specialization: 'General Physician', system: 'Allopathy', urgency: 'today', why: 'x', warn: ['x'] }; render()",
            "Finder.res = { specialization: 'General Physician', system: 'Any', urgency: 'emergency', crisis: true, why: 'x', warn: [] }; render()",
            "Finder.res = null; Finder.err = 'x'; state.filters.emerg = true; render()", "Finder.err = ''; state.filters.emerg = false; state.filters.q = 'zzzz'; render()", "state.filters.q = ''; render()",
            f"go('pDoctor', {{ id: '{DOC}' }})", f"ACT.sheet({{ k: 'request', id: '{DOC}' }})", f"state.form.mode = 'video'; render()", f"state.sheet = null; ACT.revAll({{ id: '{DOC}' }})",
            "state.sheet = null; root('pConsults')", "state.tab.pc = 'past'; render()", "state.tab.pc = 'active'; render()",
        ]
        for rid in ['q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'rA', 'r1', 'r2']:
            steps += [f"go('consult', {{ id: '{rid}' }})"]
        for rid in ['rA', 'r1', 'r2', 'q5']:
            steps += [f"go('room', {{ id: '{rid}' }})"]
        steps += ["ACT.sheet({ k: 'translate', id: 'r1' })", "state.sheet = null; state.ai['dbtr1'] = { doubts: [{ point: 'x', suggested_question: 'y' }] }; ACT.sheet({ k: 'doubts', id: 'r1', role: 'patient' })",
                  "state.ai['dbtr1'] = { busy: true }; render()", "state.ai['dbtr1'] = { doubts: [] }; render()", "state.sheet = null; render()",
                  "go('rxView', { id: 'rx1' })", "ACT.sheet({ k: 'remind', id: 'rx1' })", "state.sheet = null; ACT.sheet({ k: 'sendRx', id: 'rx1' })", "state.sheet = null; render()",
                  "root('pStores')", "ACT.sheet({ k: 'pickRx' })", "state.sheet = null; go('orderNew', {})", "go('orderNew', { rx: 'rx1' })",
                  "go('order', { id: 'o1' })", "go('order', { id: 'o2' })", "go('order', { id: 'o3' })", "go('order', { id: 'o4' })",
                  "root('alerts')", "root('profile')", "ACT.sheet({ k: 'editBasic' })", "state.sheet = null; ACT.sheet({ k: 'report', type: 'consult', id: 'r2' })",
                  "state.sheet = null; state.modal = { kind: 'rate', rid: 'r2', stars: 0, review: '' }; render()", "state.modal.stars = 4; render()", "state.modal = null; render()",
                  ]
        for s in steps: grab(s)
        keys = sorted(P.evaluate("[...I18N.collect]"))
        json.dump(keys, open('/tmp/i18n_keys_raw.json', 'w'), ensure_ascii=False, indent=0)
        print('keys', len(keys), 'errs', errs[:3])
        b.close()
finally:
    srv.terminate()
