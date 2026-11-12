import re, json, subprocess, time
from playwright.sync_api import sync_playwright
V = '13.2.0'
errs, results = [], []
def ok(name, cond, extra=''):
    results.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (' | ' + str(extra) if extra != '' else ''))
srv = subprocess.Popen(['python3', '-m', 'http.server', '8085'], cwd='/home/claude/healvio-app', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
URL = 'http://localhost:8085/'
CFG = 'window.HEALVIO_CONFIG = { production: true, firebase: { apiKey: "x", authDomain: "h.firebaseapp.com", projectId: "healvio-test", messagingSenderId: "1", appId: "1:2:web:3" }, phoneLogin: false, server: "https://w.healvio.test/", ai: true, vapidKey: "VAPID-KEY" };'
src = open('t9_calls.py').read()
exec(src[src.index("def W(p"):src.index("try:\n    with sync_playwright")].replace("8082", "8085"))
pushes, ai_calls = [], []
def push_route(route):
    req = route.request
    h = {'Access-Control-Allow-Origin': 'http://localhost:8085', 'Access-Control-Allow-Headers': 'content-type, authorization', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'}
    if req.method == 'OPTIONS': return route.fulfill(status=204, headers=h)
    pushes.append({'auth': req.headers.get('authorization'), 'body': json.loads(req.post_data)})
    route.fulfill(status=200, headers={**h, 'content-type': 'application/json'}, body='{"sent":1}')
def ice_route(route):
    route.fulfill(status=200, headers={'Access-Control-Allow-Origin': '*', 'content-type': 'application/json'}, body=json.dumps({'iceServers': [{'urls': ['stun:stun.cloudflare.com:3478']}], 'turn': False}))
def ai_route(route):
    h = {'Access-Control-Allow-Origin': 'http://localhost:8085', 'Access-Control-Allow-Headers': 'content-type, authorization'}
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=h)
    ai_calls.append(json.loads(route.request.post_data)['tier'])
    txt = json.dumps({"summary": "Fever for 3 days, likely viral.", "key_points": ["Rest", "Fluids"], "doubts_clarified": [], "instant_relief": [], "hospital_visit": "", "follow_up": "", "open_questions": []})
    route.fulfill(status=200, headers={**h, 'content-type': 'application/json'}, body=json.dumps({'text': txt}))
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        ctx.grant_permissions(['notifications'], origin='http://localhost:8085')
        def mk(f):
            body = open(f'fs_{f}.js').read()
            return lambda r: r.fulfill(status=200, content_type='application/javascript', headers={'Access-Control-Allow-Origin': '*'}, body=body)
        ctx.route(re.compile(r'https://fonts\..*'), lambda r: r.abort())
        for mod, f in [('app', 'app'), ('firestore', 'firestore'), ('auth', 'auth'), ('messaging', 'messaging_fail')]:
            ctx.route(f'https://www.gstatic.com/firebasejs/{V}/firebase-{mod}.js', mk(f))
        ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
        ctx.route('https://w.healvio.test/push', push_route)
        Q = ctx.new_page(); Q.goto(URL); W(Q, 1200)
        Q.evaluate(f"globalThis.__fsStore.set('accounts/{DOC}', {json.dumps(SEED['accounts/' + DOC])}); globalThis.__googleEmail={json.dumps(DOC_E)}")
        Q.click('button:has-text("Continue with Google")'); W(Q, 2500)
        Q.click('.banner [data-act="pushOn"]'); W(Q, 1500)
        t = Q.locator('.toast').last.inner_text() if Q.locator('.toast').count() else ''
        ok('failure names the exact Google setting to turn on', 'FCM Registration API' in t, t)
        Q.screenshot(path='p05_reason.png')
        b.close()
finally:
    srv.terminate()
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
