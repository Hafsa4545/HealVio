import re, json, subprocess, time
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['python3','-m','http.server','8084'], cwd='/home/claude/healvio-app', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
CFG = 'window.HEALVIO_CONFIG = { production: true, firebase: { apiKey: "x", authDomain: "h.firebaseapp.com", projectId: "h", appId: "1:2:web:3" }, turnUrl: "https://ai.healvio.test/ice" };'
hits = []
def ice(route):
    hits.append(route.request.url)
    route.fulfill(status=200, headers={'Access-Control-Allow-Origin': '*', 'content-type': 'application/json'}, body=json.dumps({'iceServers': [{'urls': ['stun:stun.cloudflare.com:3478', 'turn:turn.cloudflare.com:53?transport=udp', 'turn:turn.cloudflare.com:3478?transport=udp', 'turns:turn.cloudflare.com:443?transport=tcp'], 'username': 'u', 'credential': 'p'}], 'turn': True}))
try:
  with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    p = b.new_page()
    def mk(mod):
        body = open(f'fs_{mod}.js').read()
        return lambda r: r.fulfill(status=200, content_type='application/javascript', headers={'Access-Control-Allow-Origin': '*'}, body=body)
    for mod in ['app', 'firestore', 'auth']:
        p.route(f'https://www.gstatic.com/firebasejs/13.2.0/firebase-{mod}.js', mk(mod))
    p.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
    p.route('https://ai.healvio.test/ice', ice)
    p.goto('http://localhost:8084/'); p.wait_for_timeout(1000)
    a = p.evaluate("Call.iceServers()"); print('with relay:', json.dumps(a))
    c = p.evaluate("Call.iceServers()"); print('cached (1 fetch):', len(hits) == 1)
    p.unroute('https://ai.healvio.test/ice'); p.route('https://ai.healvio.test/ice', lambda r: r.abort())
    p.evaluate("Call.ice = null"); d = p.evaluate("Call.iceServers()"); print('relay down -> STUN:', json.dumps(d))
    print('port 53 removed:', not any(':53' in u for s in a for u in s['urls']), '| turn kept:', any(u.startswith('turn') for s in a for u in s['urls']))
    b.close()
finally: srv.terminate()
