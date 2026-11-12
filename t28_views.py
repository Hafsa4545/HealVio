import re, json, subprocess, time
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8101'))
KEY = 'BKrC6jePyiPug3DIb-xAkQ8G0MuJuvwQq6-jZQesTtZC5s908ulwrRZqFUyyiZPDiAuRyMGOOfDsKEygQppBETY'
CFG = CFG.replace('VAPID-KEY', KEY)
answers, push_log = [], []
def push_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    push_log.append(json.loads(route.request.post_data))
    j(route, answers.pop(0) if answers else {'sent': 1, 'phones': 1})

SWEEP = r"""(() => {
  const out = [];
  Push.last = null; LS.del('healvio:pushLast'); Push.testRes = null;
  const R = Object.values(Store.data.requests || {}), RX = Object.values(Store.data.prescriptions || {}), O = Object.values(Store.data.orders || {});
  const docs = Object.values(Store.data.accounts || {}).filter(a => a.role === 'doctor'), pats = Object.values(Store.data.accounts || {}).filter(a => a.role === 'patient');
  const ids = { req: (R[0] || {}).id, rx: (RX[0] || {}).id, order: (O[0] || {}).id, doc: (docs[0] || {}).id || (Object.values(Store.data.public || {})[0] || {}).id, pat: (pats[0] || {}).id || state.me };
  const P = v => /^(consult|room)$/.test(v) ? { id: ids.req } : /^rxView$/.test(v) ? { id: ids.rx } : /^rxEdit$/.test(v) ? { rid: ids.req, id: ids.req } : /^order$/.test(v) ? { id: ids.order } : /^orderNew$/.test(v) ? { rx: ids.rx, id: ids.rx } : /^(pDoctor|aDoctor)$/.test(v) ? { id: ids.doc } : /^patient$/.test(v) ? { id: ids.pat } : {};
  const skip = new Set(['setup', 'welcome', 'signup', 'login', 'otp', 'phoneLogin', 'completeProfile', 'dOnboard', 'sOnboard', 'accStatus']);
  for (const v of Object.keys(VIEWS)) {
    if (skip.has(v)) continue;
    const errs = []; const ce = console.error; console.error = (...a) => { errs.push(String(a[0] && a[0].message || a[0])); };
    try { state.view = v; state.params = P(v); state.stack = []; render(); } catch (e) { errs.push('throw ' + e.message); }
    console.error = ce;
    const crashed = document.body.innerText.includes('Something went wrong');
    if (crashed || errs.length) out.push(v + ': ' + (errs[0] || 'Something went wrong'));
  }
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
        ctx.route(re.compile(r'https://w\.healvio\.test/status(\?.*)?$'), lambda r: j(r, dict(status, check={'google': 'ok', 'db': 'ok', 'paypal': 'ok', 'ai': 'ok'}) if 'check=1' in r.request.url else status))
        ctx.route('https://w.healvio.test/push', push_route)
        ctx.route('https://w.healvio.test/ice', lambda r: j(r, {'iceServers': []}))
        ctx.route(re.compile(r'https://w\.healvio\.test/pay/(create|capture)$'), pay_route)
        ctx.route(re.compile(r'https://www\.paypal\.com/sdk/js.*'), sdk_route)
        ctx.route('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=FAKE_L))
        ctx.route('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', lambda r: r.fulfill(status=200, content_type='text/css', body=''))
        ctx.route(re.compile(r'https://tile\.openstreetmap\.org/.*'), lambda r: r.abort())
        pages = {}
        for who in ['D', 'P', 'S', 'A']:
            p = ctx.new_page(); p.on('pageerror', lambda e, who=who: errs.append((who, str(e))))
            p.goto(URL); W(p, 1400); pages[who] = p
        D, P, S, A = pages['D'], pages['P'], pages['S'], pages['A']
        seed(D); W(D, 400)
        A.evaluate("globalThis.__fsStore.set('accounts/ghmcinfo112gmailcom', {id:'ghmcinfo112gmailcom', role:'patient', name:'HMC', email:'hmc.info112@gmail.com', createdAt: 1}); globalThis.__fsStore.set('admins/ghmcinfo112gmailcom', {note:'owner'}); globalThis.__fsFire()"); W(A, 300)
        for p, email, name in [(D, DOC_E, 'Ananya Rao'), (P, PAT_E, 'Ravi Kumar'), (S, ST_E, 'Ramesh'), (A, 'hmc.info112@gmail.com', 'HMC')]:
            p.evaluate(f"globalThis.__googleEmail={json.dumps(email)}; globalThis.__googleName={json.dumps(name)}")
            p.click('button:has-text("Continue with Google")'); W(p, 1300)
        auid = A.evaluate("Store.authUser.uid")
        A.evaluate("globalThis.__fsStore.set('admins/%s', {note:'owner'}); globalThis.__fsStore.set('system/cron', {at: Date.now() - 2*60000, sent: 0}); globalThis.__fsFire()" % auid); W(A, 1200)
        for p in (P, D, S, A): p.evaluate("state.confirm = null; state.modal = null; state.sheet = null; render()"); W(p, 150)
        # admin home exactly as on the phone: no alert ever sent from this phone
        A.evaluate("Push.last = null; LS.del('healvio:pushLast'); state.admin = true; LS.set('healvio:admin','1'); state.stack = []; state.view = 'aHome'; state.params = {}; render()"); W(A, 1500)
        A.evaluate("render()"); W(A, 300)
        am = A.evaluate("document.body.innerText")
        ok('admin Overview opens (no "Something went wrong")', 'Something went wrong' not in am and 'System check' in am, am[:300])
        ok('admin Overview shows the live worker check', 'Worker → Google key' in am and 'Worker → database' in am, am[am.find('System check'):am.find('System check') + 900] if 'System check' in am else am[:300])
        D.evaluate("state.admin = false; state.stack = []; state.view = 'dQueue'; state.params = {}; render()"); W(D, 400)
        dq = D.evaluate("document.body.innerText")
        ok('doctor sees their real queue (not blocked)', 'This page is for doctors' not in dq and 'Something went wrong' not in dq and ('Ravi' in dq or 'clinic hours' in dq), dq[:300])
        P.evaluate("state.admin = false; state.stack = []; state.view = 'dQueue'; state.params = {}; render()"); W(P, 300)
        ok('patient who lands on the doctor page gets a friendly page', 'This page is for doctors' in P.evaluate("document.body.innerText"))
        for name, p, admin in [('patient', P, False), ('doctor', D, False), ('store', S, False), ('admin', A, True)]:
            p.evaluate("state.admin = %s" % ('true' if admin else 'false'))
            bad = p.evaluate(SWEEP)
            ok(f'{name}: every screen opens without an error', not bad, bad)
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
