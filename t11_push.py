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
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--allow-loopback-in-peer-connection'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        ctx.grant_permissions(['camera', 'microphone', 'notifications'], origin='http://localhost:8085')
        def mk(f):
            body = open(f'fs_{f}.js').read()
            return lambda r: r.fulfill(status=200, content_type='application/javascript', headers={'Access-Control-Allow-Origin': '*'}, body=body)
        ctx.route(re.compile(r'https://fonts\..*'), lambda r: r.abort())
        for mod, f in [('app', 'app'), ('firestore', 'firestore_shared'), ('auth', 'auth'), ('messaging', 'messaging')]:
            ctx.route(f'https://www.gstatic.com/firebasejs/{V}/firebase-{mod}.js', mk(f))
        ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
        ctx.route('https://w.healvio.test/push', push_route)
        ctx.route('https://w.healvio.test/ice', ice_route)
        ctx.route('https://w.healvio.test/', ai_route)
        D = ctx.new_page(); D.goto(URL); W(D, 1500)
        P = ctx.new_page(); P.goto(URL + '?go=room&id=r1'); W(P, 1500)
        for p, n in [(D, 'doctor-phone'), (P, 'patient-phone')]:
            p.on('pageerror', lambda e: errs.append(('pageerror', str(e))))
            p.evaluate(f"globalThis.__devName = '{n}'")
        ok('one worker link turns on AI, alerts and call relay', D.evaluate("[CFG().aiUrl, CFG().pushUrl, CFG().turnUrl].join(' ')") == 'https://w.healvio.test https://w.healvio.test/push https://w.healvio.test/ice', D.evaluate("[CFG().aiUrl, CFG().pushUrl, CFG().turnUrl]"))
        ok('notification link remembered before login', P.evaluate("JSON.stringify(state.pendingNav)") == '{"view":"room","id":"r1"}' and '?go' not in P.url, P.url)
        seed(D); W(D, 400)
        for p, email, name in [(D, DOC_E, 'Ananya Rao'), (P, PAT_E, 'Ravi Kumar')]:
            p.evaluate(f"globalThis.__googleEmail={json.dumps(email)}; globalThis.__googleName={json.dumps(name)}")
            p.click('button:has-text("Continue with Google")'); W(p, 1500)
        ok('tapped notification opens the consult room after login', P.evaluate("state.view") == 'room' and P.evaluate("state.params.id") == 'r1', P.evaluate("state.view"))
        ok('doctor phone registered for notifications', wait_for(D, f"/^\\[\"fcm-doctor-phone(-\\d+)?\"\\]$/.test(JSON.stringify((globalThis.__fsStore.get('pushTokens/{DOC}') || {{}}).tokens))", 6000), D.evaluate(f"globalThis.__fsStore.get('pushTokens/{DOC}')"))
        ok('patient phone registered for notifications', wait_for(P, f"/^\\[\"fcm-patient-phone(-\\d+)?\"\\]$/.test(JSON.stringify((globalThis.__fsStore.get('pushTokens/{PAT}') || {{}}).tokens))", 6000))
        D.evaluate("go('profile')"); W(D, 400)
        ok('Profile shows notifications On', D.locator('.card:has-text("Notifications on this phone") .tag:has-text("On")').count() == 1)
        D.screenshot(path='p01_profile_notifications.png')
        n0 = len(pushes)
        D.click('[data-act="pushTest"]'); W(D, 6500)
        tn = [v for k, v in D.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('notifications/') and 'notifications are working' in v.get('text', '')]
        ok('Send test notification reaches this phone', len(tn) == 1 and tn[0]['to'] == DOC and any(x['body'] == {'id': tn[0]['id']} for x in pushes[n0:]), tn)
        # alerts are pushed with the sender's sign-in
        P.evaluate(f"notify('{DOC}', 'Ravi Kumar sent a new message', {{ view: 'room', id: 'r1' }})"); W(P, 900)
        nid = P.evaluate(f"Object.keys(Object.fromEntries(globalThis.__fsStore)).filter(k => k.startsWith('notifications/')).map(k => globalThis.__fsStore.get(k)).find(n => n.text === 'Ravi Kumar sent a new message').id")
        n = P.evaluate(f"globalThis.__fsStore.get('notifications/{nid}')")
        ok('alert records who sent it', n.get('from') == PAT, n)
        ok('alert handed to the worker with sign-in', any(x['body'].get('id') == nid and x['body'].get('to') == DOC and x['auth'] == f'Bearer idtoken-{PAT}' for x in pushes), pushes[-1:])
        ok('doctor sees it in the app too', wait_for(D, f"!!Store.data.notifications['{nid}']", 4000))
        # incoming call rings the phone
        D.evaluate("go('room', { id: 'r1' })"); W(D, 500)
        D.click('[data-act="call"][data-k="video"]')
        ok('patient app rings', wait_for(P, "(document.querySelector('#call .cstat') || {}).textContent === 'Incoming video call'", 9000))
        cid = D.evaluate("Call.cur && Call.cur.id")
        ok('call also rings the phone through a notification', any(x['body'] == {'call': cid, 'n': 1} and x['auth'] == f'Bearer idtoken-{DOC}' for x in pushes), [x['body'] for x in pushes])
        W(D, 6800)
        ok('phone keeps ringing every 6 seconds', any(x['body'] == {'call': cid, 'n': 2} for x in pushes), [x['body'] for x in pushes if 'call' in x['body']])
        P.click('#call [data-c="accept"]')
        W(P, 6500)
        ok('ringing stops once answered', not any(x['body'].get('n') == 3 for x in pushes), [x['body'] for x in pushes if 'call' in x['body']])
        ok('call connects', wait_for(D, "Call.cur && Call.cur.status === 'live'", 15000) and wait_for(P, "Call.cur && Call.cur.status === 'live'", 15000))
        W(D, 1500); D.click('#call [data-c="end"]'); W(D, 2500)
        W(D, 2200)
        n0 = len(pushes)
        D.click('[data-act="call"][data-k="audio"]')
        ok('patient rings for voice call', wait_for(P, "(document.querySelector('#call .cstat') || {}).textContent === 'Incoming voice call'", 9000))
        cid2 = D.evaluate("Call.cur && Call.cur.id")
        D.click('#call [data-c="end"]'); W(D, 1500)
        new = [x['body'] for x in pushes[n0:]]
        ok('cancel: phone shows Missed voice call (replaces ringing)', {'callEnd': cid2} in new, new)
        ok('no duplicate missed-call notification', sum(1 for b in new if 'id' in b) == 0, new)
        # tapped "Answer" on the phone notification → picks up
        W(P, 2500); W(D, 2500)
        P.evaluate("navFromUrl(location.origin + '/?go=room&id=r1&answer=1')")
        D.click('[data-act="call"][data-k="video"]')
        ok('Answer on the notification picks up the call', wait_for(P, "Call.cur && ['connecting','live'].includes(Call.cur.status)", 9000) and wait_for(D, "Call.cur && Call.cur.status === 'live'", 15000), P.evaluate("Call.cur && Call.cur.status"))
        D.click('#call [data-c="end"]'); W(D, 2500)
        # AI listening + summary
        ok('AI listening shows in the consult room', D.locator('.aipill:has-text("AI listening")').count() == 1)
        P.fill('#composer', 'I have fever and body pain since 3 days'); P.click('[data-act="sendMsg"]'); W(P, 500)
        msg_n = [v for k, v in P.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('notifications/') and 'fever and body pain' in v.get('text', '')]
        ok('chat message alerts the doctor (push)', len(msg_n) == 1 and msg_n[0]['to'] == DOC and msg_n[0]['text'].startswith('Ravi Kumar: I have fever') and any(x['body'].get('id') == msg_n[0]['id'] and x['body'].get('to') == DOC for x in pushes), msg_n)
        W(P, 1600); P.fill('#composer', 'Also headache'); P.click('[data-act="sendMsg"]'); W(P, 500)
        ok('every message alerts (like WhatsApp)', len([v for k, v in P.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('notifications/') and 'headache' in v.get('text', '')]) == 1)
        ok('doctor in the room gets no duplicate pop-up', D.locator('.toast:has-text("fever and body pain")').count() == 0)
        D.click('button:has-text("End consult")'); D.click('.modal button:has-text("End consultation")'); W(D, 1200)
        btn = D.locator('[data-act="aiSummary"]')
        ok('Summarize button after the consult', btn.count() == 1)
        btn.click(); W(D, 2000)
        ok('AI summary appears', 'likely viral' in D.locator('main').inner_text() and len(ai_calls) >= 1, ai_calls)
        D.screenshot(path='p02_ai_summary.png')
        # patient got 'consult ended' style alerts pushed
        ok('ending the consult pushes alerts', sum(1 for x in pushes if 'id' in x['body']) >= 2, len(pushes))
        # logout removes this phone from the list
        P.evaluate("root('profile')"); W(P, 400)
        for sel in ['.modal button:has-text("Later")', '.modal button:has-text("Not now")']:
            if P.locator(sel).count(): P.click(sel); W(P, 300)
        P.evaluate("ACT.logout()"); W(P, 300); P.click('.modal button:has-text("Log out")'); W(P, 1200)
        ok('log out: phone stops getting that person\'s alerts', P.evaluate(f"JSON.stringify((globalThis.__fsStore.get('pushTokens/{PAT}') || {{}}).tokens)") == '[]', P.evaluate(f"globalThis.__fsStore.get('pushTokens/{PAT}')"))
        print('denied:', denied(D), denied(P))
        # first-time offer when permission not yet given
        ctx2 = b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        for mod, f in [('app', 'app'), ('firestore', 'firestore'), ('auth', 'auth'), ('messaging', 'messaging')]:
            ctx2.route(f'https://www.gstatic.com/firebasejs/{V}/firebase-{mod}.js', mk(f))
        ctx2.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
        ctx2.route(re.compile(r'https://fonts\..*'), lambda r: r.abort())
        Q = ctx2.new_page(); Q.goto(URL); W(Q, 1200)
        Q.evaluate("Object.defineProperty(Notification, 'permission', { get: () => 'default' }); Notification.requestPermission = async () => 'default';")
        Q.evaluate(f"globalThis.__fsStore.set('accounts/{PAT}', {json.dumps(SEED['accounts/' + PAT])}); globalThis.__googleEmail={json.dumps(PAT_E)}")
        Q.click('button:has-text("Continue with Google")'); W(Q, 2600)
        ok('first login offers to turn on notifications', Q.locator('.modal:has-text("Turn on notifications?")').count() == 1)
        Q.click('.modal button:has-text("Later"), .modal button:has-text("Cancel"), .modal button:has-text("Not now")'); W(Q, 500)
        ok('home keeps a Turn on notifications reminder until done', Q.locator('.banner:has-text("Turn on notifications") [data-act="pushOn"]').count() == 1)
        Q.screenshot(path='p04_home_banner.png')
        Q.screenshot(path='p03_offer.png')
        b.close()
finally:
    srv.terminate()
print('page errors:', [e for e in errs if 'fonts' not in e[-1]][:6])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
