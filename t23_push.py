import re, json, subprocess, time, base64, io
from PIL import Image
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8096'))
CFG = CFG.replace('VAPID-KEY', 'BKrC6jePyiPug3DIb-xAkQ8G0MuJuvwQq6-jZQesTtZC5s908ulwrRZqFUyyiZPDiAuRyMGOOfDsKEygQppBETY')
status.update({'refund': True, 'readRx': True, 'reminders': True, 'turn': False})
SEED['prescriptions/rxD']['medicines'] = [{'name': 'Paracetamol 650 mg 1-0-1 5 days after food, Cetirizine 10 mg 0-0-1 3 days, Dolo 650 SOS', 'dose': '', 'freq': '', 'days': '', 'note': ''}]
SEED['requests/rA']['paid'] = {'by': 'paypal', 'orderId': 'P0', 'captureId': 'CAP0', 'amount': '3.16', 'currency': 'USD', 'inr': 300, 'at': T, 'test': True}
SEED['requests/rU'] = {**SEED['requests/rA'], 'id': 'rU'}; SEED['requests/rU'].pop('paid')
SEED['requests/r2']['aiSummary'] = {'lang': 'English', 'summary': 'You had fever for 3 days.', 'key_points': ['Drink warm water'], 'instant_relief': ['Rest'], 'hospital_visit': 'If fever stays above 102.', 'follow_up': '', 'doubts_clarified': [], 'open_questions': []}
refund_log, ai_log, read_log = [], [], []
def refund_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    b = json.loads(route.request.post_data); refund_log.append({'b': b, 'auth': route.request.headers.get('authorization')})
    st = 'cancelled' if b['kind'] == 'fee' else 'unavailable'
    j(route, {'ok': True, 'refund': {'id': 'RF1', 'status': 'COMPLETED', 'amount': '3.16', 'currency': 'USD', 'inr': 300 if b['kind'] == 'fee' else 125, 'at': T + 500, 'by': 'x', 'reason': b.get('reason', '')}, 'status': st})
ai_answer = {'v': {'specialization': 'General Physician', 'system': 'Allopathy', 'urgency': 'soon', 'why': 'Fever and body pain are best checked by a general physician.', 'warn': ['Fever above 103 F', 'Trouble breathing'], 'crisis': False}}
def ai_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    b = json.loads(route.request.post_data); ai_log.append(b['prompt'])
    j(route, {'text': json.dumps(ai_answer['v'])})
def readrx_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    b = json.loads(route.request.post_data); read_log.append(b['image'][:40])
    j(route, {'medicines': [{'name': 'Augmentin 625', 'dose': '625 mg', 'freq': '1-0-1', 'days': '5', 'note': 'after food'}, {'name': 'Pan 40', 'dose': '40 mg', 'freq': '1-0-0', 'days': '5', 'note': ''}], 'readable': True})
FAKE_TTS = r"""window.__spoken = []; window.__cancels = 0;
window.SpeechSynthesisUtterance = function (t) { this.text = t; };
Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { speak(u) { window.__spoken.push({ text: u.text, lang: u.lang }); }, cancel() { window.__cancels++; }, getVoices() { return [{ lang: 'en-IN', name: 'English India' }]; } } });"""
KEY = 'BKrC6jePyiPug3DIb-xAkQ8G0MuJuvwQq6-jZQesTtZC5s908ulwrRZqFUyyiZPDiAuRyMGOOfDsKEygQppBETY'
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, geolocation=HOME, permissions=['geolocation', 'notifications'])
        ctx.add_init_script(FAKE_TTS)
        def mk(f):
            body = open(f'fs_{f}.js').read()
            return lambda r: r.fulfill(status=200, content_type='application/javascript', headers={'Access-Control-Allow-Origin': '*'}, body=body)
        ctx.route(re.compile(r'https://fonts\..*'), lambda r: r.abort())
        for mod, f in [('app', 'app'), ('firestore', 'firestore_shared'), ('auth', 'auth'), ('messaging', 'messaging')]:
            ctx.route(f'https://www.gstatic.com/firebasejs/{V}/firebase-{mod}.js', mk(f))
        ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
        ctx.route('https://w.healvio.test/status', lambda r: j(r, status))
        ctx.route('https://w.healvio.test/push', lambda r: j(r, {'sent': 1}))
        ctx.route('https://w.healvio.test/ice', lambda r: j(r, {'iceServers': []}))
        ctx.route('https://w.healvio.test/pay/refund', refund_route)
        ctx.route(re.compile(r'https://w\.healvio\.test/pay/(create|capture)$'), pay_route)
        ctx.route('https://w.healvio.test/read-rx', readrx_route)
        ctx.route('https://w.healvio.test/', ai_route)
        ctx.route(re.compile(r'https://www\.paypal\.com/sdk/js.*'), sdk_route)
        ctx.route('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=FAKE_L))
        ctx.route('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', lambda r: r.fulfill(status=200, content_type='text/css', body=''))
        ctx.route(re.compile(r'https://nominatim\.openstreetmap\.org/reverse.*'), nominatim)
        pages = {}
        for who in ['D', 'P', 'S']:
            p = ctx.new_page(); p.on('pageerror', lambda e, who=who: errs.append((who, str(e))))
            p.goto(URL); W(p, 1400); pages[who] = p
        D, P, S = pages['D'], pages['P'], pages['S']
        seed(D); W(D, 400)
        for p, email, name in [(D, DOC_E, 'Ananya Rao'), (P, PAT_E, 'Ravi Kumar'), (S, ST_E, 'Ramesh')]:
            p.evaluate(f"globalThis.__googleEmail={json.dumps(email)}; globalThis.__googleName={json.dumps(name)}")
            p.click('button:has-text("Continue with Google")'); W(p, 1200)
        clear = lambda p: (p.evaluate("state.confirm = null; state.modal = null; state.sheet = null; render()"), W(p, 150))
        W(P, 1500)
        for p in (P, D, S): clear(p)
        mainP = lambda: P.locator('main').inner_text()
        notes_to = lambda who: [v['text'] for k, v in P.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('notifications/') and v.get('to') == who]


        P.evaluate("Notification.requestPermission ? 0 : 0")
        perm = P.evaluate("Notification.permission")
        print('perm', perm)
        P.evaluate(f"globalThis.__realKey = {json.dumps(KEY)}")
        def reg(mode):
            return P.evaluate("(async m => { globalThis.__pushMode = m; globalThis.__gt = []; Push.api = undefined; Push.token = ''; const ok = await Push.register(); return [ok, globalThis.__gt, Push.err ? String(Push.err.message || Push.err) : '', window.healvioBackend.vapidOk]; })", mode)
        r = reg('')
        ok('valid key from config.js is used first', r[0] is True and r[1] == ['key'] and r[3] is True, r)
        r = reg('keyfail')
        ok('key rejected on this phone → cleared and retried, then Firebase key works', r[0] is True and r[1] == ['key', 'key', 'default'], r)
        tk = P.evaluate("globalThis.__fsStore.get('pushTokens/' + Store.authUser.uid)")
        ok('phone address saved for alerts', tk and len(tk['tokens']) >= 1, tk)
        r = reg('allfail')
        why = P.evaluate("Push.why()")
        ok('if Google cannot be reached at all → clear phone steps', r[0] is False and 'Private DNS' in why and 'Google Play services' in why, why)
        ok('bad key in config.js is detected', P.evaluate("window.healvioBackend.vapidCheck('BGlv62avAXtSY7MDgVxryI1').then(x => x)") is False and P.evaluate(f"window.healvioBackend.vapidCheck({json.dumps(KEY)})") is True)
        P.evaluate("globalThis.__pushMode = ''")
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
