import re, json, subprocess, time
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8098'))
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
        for mod, f in [('app', 'app'), ('firestore', 'firestore_shared'), ('auth', 'auth'), ('messaging', 'messaging')]:
            ctx.route(f'https://www.gstatic.com/firebasejs/{V}/firebase-{mod}.js', mk(f))
        ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
        ctx.route('https://w.healvio.test/status', lambda r: j(r, status))
        ctx.route('https://w.healvio.test/push', push_route)
        ctx.route('https://w.healvio.test/ice', lambda r: j(r, {'iceServers': []}))
        ctx.route(re.compile(r'https://w\.healvio\.test/pay/(create|capture)$'), pay_route)
        ctx.route(re.compile(r'https://www\.paypal\.com/sdk/js.*'), sdk_route)
        ctx.route('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=FAKE_L))
        ctx.route('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', lambda r: r.fulfill(status=200, content_type='text/css', body=''))
        pages = {}
        for who in ['D', 'P']:
            p = ctx.new_page(); p.on('pageerror', lambda e, who=who: errs.append((who, str(e))))
            p.goto(URL); W(p, 1400); pages[who] = p
        D, P = pages['D'], pages['P']
        seed(D); W(D, 400)
        for p, email, name in [(D, DOC_E, 'Ananya Rao'), (P, PAT_E, 'Ravi Kumar')]:
            p.evaluate(f"globalThis.__googleEmail={json.dumps(email)}; globalThis.__googleName={json.dumps(name)}")
            p.click('button:has-text("Continue with Google")'); W(p, 1200)
        clear = lambda p: (p.evaluate("state.confirm = null; state.modal = null; state.sheet = null; render()"), W(p, 150))
        W(P, 1500)
        for p in (P, D): clear(p)
        P.evaluate(f"globalThis.__realKey = {json.dumps(KEY)}; globalThis.__devName = 'pat'")
        # make sure this phone is registered
        okreg = P.evaluate("(async () => { Push.api = undefined; return await Push.register(); })()")
        tok0 = P.evaluate("globalThis.__fsStore.get('pushTokens/' + Store.authUser.uid).tokens.slice(-1)[0]")
        ok('phone registered', okreg is True and tok0.startswith('fcm-pat'), tok0)

        def run_test(ans, wait=7500):
            answers[:] = ans; push_log.clear()
            P.evaluate("Push.testRes = null; root('profile')"); W(P, 500)
            P.click('button:has-text("Send test notification")'); W(P, wait)
            P.evaluate("render()"); W(P, 300)
            return P.locator('main').inner_text()

        # 0. admin System check when this phone has never sent an alert (crashed in the 105022 build)
        r0 = P.evaluate("(() => { Push.last = null; LS.del('healvio:pushLast'); try { const h = SysCheck.html(); return h.includes('Phone notifications') ? 'ok' : 'missing row'; } catch (e) { return 'CRASH: ' + e.message; } })()")
        ok('System check works before any alert was ever sent (no crash)', r0 == 'ok', r0)
        # 1. normal
        t = run_test([{'sent': 1, 'phones': 1}])
        ok('test OK: result line stays on screen with phone tips', 'Test at' in t and 'Sent ✓' in t and 'Pop on screen' in t, t[-400:])
        ok('test sent the alert id to the worker', len(push_log) == 1 and 'id' in push_log[0], push_log)

        # 2. dead address → app makes a new one by itself and tries again
        t = run_test([{'sent': 0, 'phones': 1, 'gone': 1}, {'sent': 1, 'phones': 1}], 9500)
        tok1 = P.evaluate("globalThis.__fsStore.get('pushTokens/' + Store.authUser.uid).tokens.slice(-1)[0]")
        ok('dead address: new address made and saved, test tried again and worked', len(push_log) == 2 and tok1 != tok0 and 'Sent ✓' in t, [tok0, tok1, len(push_log), t[-200:]])

        # 3. database free limit
        t = run_test([{'sent': 0, 'error': 'free_limit'}])
        ok('free limit: says so in plain words with the reset time', 'free daily database limit' in t and '1:30 PM' in t and len(push_log) == 1, t[-300:])

        # 4. Google refuses (API off)
        fcm = 'error 403 PERMISSION_DENIED Firebase Cloud Messaging API has not been used in project healvio before or it is disabled.'
        t = run_test([{'sent': 0, 'phones': 1, 'fcm': fcm}, {'sent': 0, 'phones': 1, 'fcm': fcm}], 9500)
        ok('Google refuses: tells exactly which setting to turn on (no needless re-register)', 'Firebase Cloud Messaging API' in t and 'turn on' in t.lower() and len(push_log) == 1, [len(push_log), t[-300:]])
        t = run_test([{'sent': 0, 'phones': 1, 'fcm': 'error 403 SENDER_ID_MISMATCH SenderId mismatch'}, {'sent': 1, 'phones': 1}], 9500)
        ok('phone registered to another project: re-registered by itself and works', len(push_log) == 2 and 'Sent ✓' in t, [len(push_log), t[-200:]])

        # 5. service account key
        t = run_test([{'error': 'google_login', 'detail': 'Google sign-in for the service account failed: Invalid JWT Signature.'}])
        ok('worker cannot sign in to Google: says to make a new service account key', 'FIREBASE_SERVICE_ACCOUNT' in t and 'Generate new private key' in t, t[-400:])

        # 6. worker unreachable
        ctx.unroute('https://w.healvio.test/push')
        ctx.route('https://w.healvio.test/push', lambda r: r.abort())
        t = run_test([])
        ok("worker unreachable: says can't reach your worker", "Can't reach your worker" in t, t[-300:])
        ctx.unroute('https://w.healvio.test/push')
        ctx.route('https://w.healvio.test/push', push_route)

        # 7. self-repair at app start: address removed by the worker → new one made
        P.evaluate("(() => { const id = Store.authUser.uid; globalThis.__fsStore.set('pushTokens/' + id, { id, tokens: [] }); })()")
        before = P.evaluate("LS.get('healvio:pushToken')")
        r = P.evaluate("(async () => { Push.healed = false; Push.token = ''; return await Push.register(); })()")
        after = P.evaluate("globalThis.__fsStore.get('pushTokens/' + Store.authUser.uid).tokens")
        ok('app start: address removed by worker (dead) → a new one is made and saved', r is True and after and after[-1] != before, [before, after])
        r = P.evaluate("(async () => { Push.token = ''; return await Push.register(); })()")
        after2 = P.evaluate("globalThis.__fsStore.get('pushTokens/' + Store.authUser.uid).tokens")
        ok('normal app start: same address kept, nothing re-made', r is True and after2 == after, [after, after2])

        # 8. a real alert to someone without notifications: recorded clearly, System check not alarmed
        answers[:] = [{'sent': 0, 'phones': 0}]
        P.evaluate("notify(" + json.dumps(DOC) + ", 'Test message to doctor', { view: 'alerts' }, 'info')"); W(P, 1200)
        ls = P.evaluate("Push.lastSend()")
        ok('last alert remembered in plain words', ls and ls['other'] is True and 'not turned on notifications' in ls['text'], ls)
        html = P.evaluate("SysCheck.html()")
        i = html.find('Phone notifications')
        ok('System check shows the last alert result (still ✅: the system works)', 'last alert' in html and 'not turned on notifications' in html and '✅' in html[i - 80:i] and '⚠️' not in html[i - 80:i], html[i - 80: i + 250])
        answers[:] = [{'sent': 0, 'error': 'free_limit'}]
        P.evaluate("notify(" + json.dumps(DOC) + ", 'Another message', { view: 'alerts' }, 'info')"); W(P, 1200)
        html = P.evaluate("SysCheck.html()")
        i = html.find('Phone notifications'); seg = html[i - 80: i + 300]
        ok('System check warns when alerts fail', '⚠️' in html[i - 80:i] and 'free daily database limit' in seg, seg)

        # 9. live check of the worker (admin System check)
        check, st_auth = {'v': None}, []
        def status_route(route):
            if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
            st = dict(status)
            if 'check=1' in route.request.url:
                st_auth.append(route.request.headers.get('authorization', ''))
                if check['v'] is not None: st['check'] = check['v']
            j(route, st)
        ctx.route(re.compile(r'https://w\.healvio\.test/status(\?.*)?$'), status_route)
        def deep(v):
            check['v'] = v
            P.evaluate("SysCheck.loadDeep(true)"); W(P, 1200)
            return P.evaluate("SysCheck.html()")
        def mark(html, name):
            i = html.find(name); return html[i - 80:i] if i >= 0 else 'MISSING'
        html = deep({'google': 'Google sign-in for the service account failed: invalid_grant: Invalid JWT Signature.', 'paypal': 'ok', 'ai': 'free_limit'})
        ok('live check: broken Google key named with the exact fix', '⚠️' in mark(html, 'Worker → Google key') and 'Invalid JWT Signature' in html and 'Generate new private key' in html and 'FIREBASE_SERVICE_ACCOUNT' in html, html[html.find('Live check') - 10: html.find('Live check') + 10] if 'Live check' in html else html[-900:])
        ok('live check: AI free limit with reset time', '⚠️' in mark(html, 'Worker → AI') and '5:30 AM' in html)
        ok('live check: PayPal OK shown OK', '✅' in mark(html, 'Worker → PayPal'))
        ok('live check sends the sign-in token', st_auth and st_auth[-1].startswith('Bearer ') and len(st_auth[-1]) > 12, st_auth[-1:])
        html = deep({'google': 'ok', 'db': 'free_limit', 'paypal': 'PayPal sign-in failed. Check PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET (use the Sandbox keys): invalid_client', 'ai': 'ok'})
        ok('live check: database free limit and PayPal key problem', '⚠️' in mark(html, 'Worker → database') and '1:30 PM' in html and '⚠️' in mark(html, 'Worker → PayPal') and 'invalid_client' in html and 'Apps & Credentials' in html, [mark(html, 'Worker → database'), mark(html, 'Worker → PayPal'), html[html.find('Worker → database'):html.find('Worker → database') + 600]])
        html = deep({'google': 'ok', 'db': 'ok', 'paypal': 'ok', 'ai': 'ok'})
        ok('live check: all four parts ✅ when working', all('✅' in mark(html, n) for n in ['Worker → Google key', 'Worker → database', 'Worker → PayPal', 'Worker → AI']))
        html = deep(None)
        ok('old worker: asks to paste the newest worker', 'Paste the newest ai-server/worker.js' in html)
        check['v'] = {'google': 'ok', 'db': 'ok', 'paypal': 'ok', 'ai': 'ok'}
        P.evaluate("SysCheck.deep = null; root('aHome')"); W(P, 300)

        # 10. payment: the worker's real reason is shown (not only "Payment failed")
        def pay_fail(route):
            if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
            j(route, {'error': 'Payment failed. Please try again.', 'detail': 'Google sign-in for the service account failed: invalid_grant'}, 502)
        ctx.route(re.compile(r'https://w\.healvio\.test/pay/(create|capture)$'), pay_fail)
        clear(P); P.evaluate("go('consult', { id: 'rA' })"); W(P, 700)
        P.click('[data-act="payFee"]'); W(P, 1500)
        P.click('#fake-pp'); W(P, 1200)
        m = P.locator('#pp-msg').inner_text()
        ok("payment error shows the worker's reason", 'Payment failed' in m and 'service account' in m, m)
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
