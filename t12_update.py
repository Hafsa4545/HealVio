import re, json, subprocess, time
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['python3', '-m', 'http.server', '8086'], cwd='/home/claude/healvio-app', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
V = '13.2.0'; res = []
def ok(n, c, x=''): res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x) if x != '' else ''))
CFG = 'window.HEALVIO_CONFIG = { production: true, firebase: { apiKey: "x", authDomain: "h.firebaseapp.com", projectId: "h", appId: "1:2:web:3" } };'
ver = {'v': json.load(open('/home/claude/healvio-app/version.json'))['v']}
loads = []
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = b.new_context()
        def mk(f):
            body = open(f'fs_{f}.js').read()
            return lambda r: r.fulfill(status=200, content_type='application/javascript', headers={'Access-Control-Allow-Origin': '*'}, body=body)
        for mod in ['app', 'firestore', 'auth']: ctx.route(f'https://www.gstatic.com/firebasejs/{V}/firebase-{mod}.js', mk(mod))
        ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
        ctx.route(re.compile(r'.*/version\.json.*'), lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(ver)))
        ctx.route(re.compile(r'https://fonts\..*'), lambda r: r.abort())
        p = ctx.new_page(); p.on('load', lambda: loads.append(1))
        p.goto('http://localhost:8086/'); p.wait_for_timeout(5500)
        ok('same version: no reload', len(loads) == 1, len(loads))
        p.evaluate("window.__old = 1")
        ver['v'] = 'NEW-BUILD'
        p.evaluate("Call.cur = { id: 'x' }; document.dispatchEvent(new Event('visibilitychange'))"); p.wait_for_timeout(1500)
        ok('during a call: waits, no reload', p.evaluate("window.__old === 1 && state.updateWaiting === true"))
        p.evaluate("Call.cur = null; document.dispatchEvent(new Event('visibilitychange'))"); p.wait_for_timeout(2500)
        ok('new version: app reloads itself when reopened', len(loads) == 2 and p.evaluate("window.__old === undefined"), len(loads))
        p.evaluate("document.dispatchEvent(new Event('visibilitychange'))"); p.wait_for_timeout(2500)
        ok('never reloads in a loop', len(loads) == 2, len(loads))
        b.close()
finally: srv.terminate()
print('PASSED %d / %d' % (sum(res), len(res)))
