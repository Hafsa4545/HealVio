import re, json, subprocess, time, sys
from playwright.sync_api import sync_playwright
V = '13.2.0'
PHOTO = open('/tmp/photo.txt').read()
CFG = 'window.HEALVIO_CONFIG = { production: true, firebase: { apiKey: "x", authDomain: "h.firebaseapp.com", projectId: "h", appId: "1:2:web:3" } };'
T = int(time.time() * 1000)
def gid(e): return 'g' + re.sub(r'\W', '', e)
PAT_E = 'ravi.kumar@example.com'; PAT = gid(PAT_E)
seed = {f'accounts/{PAT}': {'id': PAT, 'role': 'patient', 'name': 'Ravi Kumar', 'email': PAT_E, 'phone': '9000000002', 'age': 30, 'status': 'active', 'createdAt': T}}
for i in range(30):
    d = f'doc{i}'
    info = {'photo': PHOTO[:-8] + format(i, '08d').replace('0','A') if False else PHOTO, 'system': ['Ayurveda','Homeopathy','Allopathy'][i % 3], 'specialization': 'General', 'degree': 'MBBS', 'experience': 5 + i, 'hospital': f'Hospital {i}', 'hospitalAddress': 'Road', 'city': 'Hyderabad', 'fee': 300,
            'days': [0,1,2,3,4,5,6], 'start': '00:00', 'end': '23:59', 'slot': 15, 'emergencySlots': 2, 'languages': 'English', 'regNo': f'R{i}', 'about': 'x', 'sigFile': ''}
    seed[f'public/{d}'] = {'id': d, 'role': 'doctor', 'name': f'Doctor {i}', 'status': 'approved', 'demo': False, 'doc': info}
seed['requests/r1'] = {'id': 'r1', 'patientId': PAT, 'doctorId': 'doc0', 'status': 'live', 'mode': 'chat', 'type': 'normal', 'problem': 'x', 'createdAt': T, 'patient': {'name': 'Ravi', 'age': 30, 'phone': '1'}, 'prefDate': '2026-11-10', 'slotDate': '2026-11-10', 'slotTime': '10:00', 'rateSkipped': True}
for k in range(150):
    m = {'id': f'm{k:03d}', 'from': PAT if k % 2 else 'doc0', 'text': f'Message number {k} about symptoms and medicines', 'at': T - (150 - k) * 1000}
    if k % 15 == 0: m['image'] = PHOTO; m['text'] = ''
    seed[f'requests/r1/messages/m{k:03d}'] = m
def run(root, port, label):
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(port)], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
            ctx = b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
            def mk(f):
                body = open(f'fs_{f}.js').read()
                return lambda r: r.fulfill(status=200, content_type='application/javascript', headers={'Access-Control-Allow-Origin': '*'}, body=body)
            ctx.route(re.compile(r'https://fonts\..*'), lambda r: r.abort())
            for mod in ['app', 'firestore', 'auth']: ctx.route(f'https://www.gstatic.com/firebasejs/{V}/firebase-{mod}.js', mk(mod))
            ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
            p = ctx.new_page()
            cdp = ctx.new_cdp_session(p); cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})  # like a budget phone
            p.goto(f'http://localhost:{port}/'); p.wait_for_timeout(1500)
            p.evaluate("(seed) => { for (const [k, v] of Object.entries(seed)) globalThis.__fsStore.set(k, v); }", seed)
            p.evaluate(f"globalThis.__googleEmail={json.dumps(PAT_E)}")
            p.click('button:has-text("Continue with Google")'); p.wait_for_timeout(3000)
            out = {}
            for view, js in [('doctor list', "root('pHome')"), ('chat (150 msgs, 10 photos)', "go('room', { id: 'r1' })")]:
                p.evaluate(js); p.wait_for_timeout(1500)
                ms = p.evaluate("""() => { const t0 = performance.now(); for (let i = 0; i < 20; i++) render(); return (performance.now() - t0) / 20; }""")
                size = p.evaluate("document.getElementById('app').innerHTML.length")
                if 'chat' in view:
                    print('blob creations in 10 builds:', p.evaluate("() => { let n = 0; const o = URL.createObjectURL; URL.createObjectURL = b => { n++; return o(b); }; for (let i = 0; i < 10; i++) VIEWS.room(state.params); URL.createObjectURL = o; return n; }"))
                    print('msgs:', p.evaluate("(state.msgs[state.params.id] || []).length"), 'imgs:', p.evaluate("(state.msgs[state.params.id] || []).filter(m => m.image).length"))
                    print('t loop only:', p.evaluate("() => { const L = state.msgs[state.params.id]; const t0 = performance.now(); for (let i = 0; i < 10; i++) L.forEach(m => imgSrc(m.image)); return (performance.now() - t0) / 10; }"))
                    print('t esc only:', p.evaluate("() => { const L = state.msgs[state.params.id]; const t0 = performance.now(); for (let i = 0; i < 10; i++) L.forEach(m => esc(m.text || '')); return (performance.now() - t0) / 10; }"))
                    cdp.send('Profiler.enable'); cdp.send('Profiler.start')
                    p.evaluate("() => { for (let i = 0; i < 30; i++) VIEWS.room(state.params); }")
                    prof = cdp.send('Profiler.stop')['profile']
                    nodes = {n['id']: n for n in prof['nodes']}
                    self_t = {}
                    dt = prof['timeDeltas']; samples = prof['samples']
                    for sid, d in zip(samples, dt):
                        n = nodes[sid]; key = n['callFrame']['functionName'] or '(anon)'; key += ':' + str(n['callFrame']['lineNumber'])
                        self_t[key] = self_t.get(key, 0) + d
                    for k, v in sorted(self_t.items(), key=lambda x: -x[1])[:12]: print('  ', k, round(v/1000, 1), 'ms')
                out[view] = (round(ms, 1), size)
            b.close()
            return out
    finally:
        srv.terminate()
old = {}; new = run('/home/claude/healvio-app', 8092, 'new')
for k in new:
    print(k, new[k])
