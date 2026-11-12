import re, json, subprocess, time
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8099'))
KEY = 'BKrC6jePyiPug3DIb-xAkQ8G0MuJuvwQq6-jZQesTtZC5s908ulwrRZqFUyyiZPDiAuRyMGOOfDsKEygQppBETY'
CFG = CFG.replace('VAPID-KEY', KEY)
answers, push_log = [], []
def push_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    push_log.append(json.loads(route.request.post_data))
    j(route, answers.pop(0) if answers else {'sent': 1, 'phones': 1})

try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, geolocation=HOME, permissions=['geolocation', 'notifications'])
        def mk(f):
            body = open(f'fs_{f}.js').read()
            return lambda r: r.fulfill(status=200, content_type='application/javascript', headers={'Access-Control-Allow-Origin': '*'}, body=body)
        ctx.route(re.compile(r'https://fonts\..*'), lambda r: r.abort())
        for mod, f in [('app', 'app'), ('firestore', 'firestore_cache'), ('auth', 'auth'), ('messaging', 'messaging')]:
            ctx.route(f'https://www.gstatic.com/firebasejs/{V}/firebase-{mod}.js', mk(f))
        ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
        ctx.route(re.compile(r'https://w\.healvio\.test/status(\?.*)?$'), lambda r: j(r, status))
        ctx.route('https://w.healvio.test/push', push_route)
        ctx.route('https://w.healvio.test/ice', lambda r: j(r, {'iceServers': []}))
        D = ctx.new_page(); D.on('pageerror', lambda e: errs.append(('D', str(e)))); D.goto(URL); W(D, 1400)
        P = ctx.new_page(); P.on('pageerror', lambda e: errs.append(('P', str(e)))); P.goto(URL); W(P, 1400)
        seed(D); W(D, 400)
        ok('phone keeps a copy of the data (offline cache on)', P.evaluate("window.healvioBackend.cacheOn") is True)
        init = P.evaluate("globalThis.__fsInit")
        ok('cache works across several open tabs/app windows', init and 'persistent' in init[0] and 'multi-tab' in init[0], init)
        P.evaluate(f"globalThis.__googleEmail={json.dumps(PAT_E)}; globalThis.__googleName='Ravi Kumar'")
        P.click('button:has-text("Continue with Google")'); W(P, 1800)
        P.evaluate("state.confirm = null; state.modal = null; state.sheet = null; render()"); W(P, 200)
        ok('login and data load normally with the cache', P.evaluate("!!me() && me().role === 'patient' && Object.keys(Store.data.requests).length > 0"), P.evaluate("[!!me(), Object.keys(Store.data.requests).length]"))
        # log out → the copy on the phone is wiped and the app starts fresh
        P.evaluate("root('profile')"); W(P, 400)
        P.click('button:has-text("Log out")'); W(P, 300)
        P.click('.sheet button:has-text("Log out"), .modal button:has-text("Log out"), .confirm button:has-text("Log out")'); W(P, 2500)
        wiped = P.evaluate("[localStorage.getItem('__fsTerm'), localStorage.getItem('__fsClear')]")
        ok('log out: phone copy of health data wiped (terminate + clear)', wiped == ['1', '1'], wiped)
        ok('after log out: welcome screen, nobody logged in', P.locator('button:has-text("Continue with Google")').count() == 1 and P.evaluate("!me()"), P.evaluate("document.body.innerText.slice(0, 200)"))
        # log in again works
        P.evaluate(f"globalThis.__googleEmail={json.dumps(PAT_E)}; globalThis.__googleName='Ravi Kumar'")
        P.click('button:has-text("Continue with Google")'); W(P, 1800)
        ok('log in again after the wipe works', P.evaluate("!!me() && Object.keys(Store.data.requests).length > 0"))
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
