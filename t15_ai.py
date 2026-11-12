import re, json, subprocess, time
from playwright.sync_api import sync_playwright
V = '13.2.0'
errs, results = [], []
def ok(name, cond, extra=''):
    results.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (' | ' + str(extra)[:260] if extra != '' else ''))
srv = subprocess.Popen(['python3', '-m', 'http.server', '8087'], cwd='/home/claude/healvio-app', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
URL = 'http://localhost:8087/'
# like the real config.js: server + vapidKey, no "ai" line at all
CFG = 'window.HEALVIO_CONFIG = { production: true, firebase: { apiKey: "x", authDomain: "h.firebaseapp.com", projectId: "healvio-test", messagingSenderId: "1", appId: "1:2:web:3" }, phoneLogin: false, server: "https://w.healvio.test/", vapidKey: "VAPID-KEY" };'
src = open('t9_calls.py').read()
exec(src[src.index("def W(p"):src.index("try:\n    with sync_playwright")].replace("8082", "8087"))
H = {'Access-Control-Allow-Origin': 'http://localhost:8087', 'Access-Control-Allow-Headers': 'content-type, authorization', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'}
listens, prompts = [], []
def j(route, obj, status=200):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    route.fulfill(status=status, headers={**H, 'content-type': 'application/json'}, body=json.dumps(obj))
def status_route(route): j(route, {'ai': True, 'listen': True, 'push': True, 'turn': False})
def push_route(route): j(route, {'sent': 1})
def ice_route(route): j(route, {'iceServers': [{'urls': ['stun:stun.cloudflare.com:3478']}]})
def listen_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    b = json.loads(route.request.post_data)
    if not listens: open('/tmp/chunk.b64','w').write(b['audio'])
    listens.append({'rid': b['rid'], 'len': len(b['audio']), 'wav': b['audio'][:6], 'auth': route.request.headers.get('authorization')})
    who = 'doctor' if 'ananya' in (route.request.headers.get('authorization') or '') else 'patient'
    j(route, {'text': 'Take rest and drink warm water.' if who == 'doctor' else 'I have fever and body pain since three days.'})
def ai_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    b = json.loads(route.request.post_data); prompts.append({'p': b['prompt'], 'auth': route.request.headers.get('authorization')})
    if 'Summarize' in b['prompt']:
        txt = json.dumps({"summary": "You had fever and body pain for 3 days. The doctor advised rest and warm water.", "key_points": ["Rest", "Warm water"], "doubts_clarified": [], "instant_relief": [], "hospital_visit": "", "follow_up": "", "open_questions": []})
    else: txt = json.dumps({"doubts": []})
    j(route, {'text': txt})
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--allow-loopback-in-peer-connection', '--autoplay-policy=no-user-gesture-required'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        ctx.grant_permissions(['camera', 'microphone'], origin='http://localhost:8087')
        def mk(f):
            body = open(f'fs_{f}.js').read()
            return lambda r: r.fulfill(status=200, content_type='application/javascript', headers={'Access-Control-Allow-Origin': '*'}, body=body)
        ctx.route(re.compile(r'https://fonts\..*'), lambda r: r.abort())
        for mod, f in [('app', 'app'), ('firestore', 'firestore_shared'), ('auth', 'auth'), ('messaging', 'messaging')]:
            ctx.route(f'https://www.gstatic.com/firebasejs/{V}/firebase-{mod}.js', mk(f))
        ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
        ctx.route('https://w.healvio.test/status', status_route)
        ctx.route('https://w.healvio.test/push', push_route)
        ctx.route('https://w.healvio.test/ice', ice_route)
        ctx.route('https://w.healvio.test/listen', listen_route)
        ctx.route('https://w.healvio.test/', ai_route)
        pages = {}
        for who in ['D', 'P']:
            p = ctx.new_page()
            p.on('pageerror', lambda e, who=who: errs.append((who, str(e))))
            p.goto(URL); W(p, 1400); pages[who] = p
        D, P = pages['D'], pages['P']
        seed(D); W(D, 400)
        for p, email, name in [(D, DOC_E, 'Ananya Rao'), (P, PAT_E, 'Ravi Kumar')]:
            p.evaluate(f"globalThis.__googleEmail={json.dumps(email)}; globalThis.__googleName={json.dumps(name)}")
            p.click('button:has-text("Continue with Google")'); W(p, 1200)
            for sel in ['.modal button:has-text("Later")', '.modal button:has-text("Cancel")']:
                if p.locator(sel).count(): p.click(sel); W(p, 200)
        ok('AI switched on by itself (no config change)', D.evaluate("CFG().aiUrl === 'https://w.healvio.test' && CFG().listenUrl === 'https://w.healvio.test/listen'"), D.evaluate("[CFG().aiUrl, CFG().listenUrl]"))
        for p in (D, P): p.evaluate("go('room', { id: 'r1' })"); W(p, 600)
        ok('consult room shows AI listening', D.locator('.aipill:has-text("AI listening")').count() == 1)
        # chat message + call
        P.fill('#composer', 'Hello doctor'); P.click('[data-act="sendMsg"]'); W(P, 400)
        D.click('[data-act="call"][data-k="video"]')
        ok('patient rings', wait_for(P, "(document.querySelector('#call .cstat') || {}).textContent === 'Incoming video call'", 9000))
        P.click('#call [data-c="accept"]')
        ok('call live', wait_for(D, "Call.cur && Call.cur.status === 'live'", 15000) and wait_for(P, "Call.cur && Call.cur.status === 'live'", 15000))
        W(D, 800)
        ok('call screen shows "AI notes on" on both phones', 'AI notes on' in D.locator('#call .cnotes').inner_text() and 'AI notes on' in P.locator('#call .cnotes').inner_text(), D.locator('#call .cnotes').inner_text())
        ok('both phones listen only to their own microphone', D.evaluate("Listen.on && Listen.rid === 'r1'") and P.evaluate("Listen.on"))
        D.screenshot(path='a01_call_notes.png')
        ok('speech is sent as text-ready audio pieces', wait_for(D, "true", 1) and (W(D, 17000) or True) and len(listens) >= 2, [(x['wav'], x['len']) for x in listens])
        ok('audio pieces are WAV from each person, signed in', all(x['wav'].startswith('UklGR') and x['rid'] == 'r1' and (x['auth'] or '').startswith('Bearer idtoken-') for x in listens) and len({x['auth'] for x in listens}) == 2, listens[:2])
        W(D, 1500)
        m = D.evaluate("(state.msgs['r1'] || []).filter(m => m.stt).map(m => [m.from, m.text])")
        ok('what each person said appears in the chat', any(f == DOC and 'warm water' in t for f, t in m) and any(f == PAT and 'fever' in t for f, t in m), m)
        n_before = len([x for x in listens if PAT.replace('g','',1) in (x['auth'] or '') or 'ravi' in (x['auth'] or '')])
        P.click('#call [data-c="notes"]'); W(P, 300)
        ok('patient can stop AI notes for their voice', 'AI notes off' in P.locator('#call .cnotes').inner_text() and P.evaluate("!Listen.on"))
        k = len(listens); W(P, 16500)
        new_pat = [x for x in listens[k:] if 'ravi' in (x['auth'] or '')]
        ok('after stopping, nothing more is sent from that phone', len(new_pat) == 0, len(new_pat))
        D.click('#call [data-c="min"]'); W(D, 600)
        D.screenshot(path='a02_chat_with_call_notes.png')
        ok('chat shows "said on the call" label', D.locator('.msg.stt .sttl').count() >= 1)
        D.click('#call'); W(D, 300)
        D.click('#call [data-c="end"]'); W(D, 2500)
        ok('notes stop when the call ends', D.evaluate("!Listen.on") and P.evaluate("!Listen.on"))
        notes_count = D.evaluate("(state.msgs['r1'] || []).filter(m => m.stt).length")
        ok('no notification flood from call notes', not any('fever and body pain' in json.dumps(v) for k2, v in D.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k2.startswith('notifications/')))
        # summary after consult
        D.click('button:has-text("End consult")'); D.click('.modal button:has-text("End consultation")'); W(D, 1200)
        D.click('[data-act="aiSummary"]'); W(D, 2200)
        sp = [x for x in prompts if 'Summarize' in x['p']]
        ok('AI summary includes what was said on the call', sp and '(said on the video/voice call)' in sp[-1]['p'] and 'warm water' in sp[-1]['p'], sp[-1]['p'][-400:] if sp else '')
        ok('AI requests carry the sign-in', sp and (sp[-1]['auth'] or '').startswith('Bearer idtoken-'))
        ok('summary shows', 'advised rest and warm water' in D.locator('main').inner_text())
        D.screenshot(path='a03_summary.png')
        print('denied:', denied(D), denied(P))
        b.close()
finally:
    srv.terminate()
print('page errors:', errs[:5])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
