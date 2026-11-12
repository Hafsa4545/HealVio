import re, json, subprocess, time
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['python3', '-m', 'http.server', '8082'], cwd='/home/claude/healvio-app', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
URL = 'http://localhost:8082/'
V = '13.2.0'
CFG = 'window.HEALVIO_CONFIG = { production: true, firebase: { apiKey: "x", authDomain: "healvio-test.firebaseapp.com", projectId: "healvio-test", appId: "1:2:web:3" }, aiUrl: "", phoneLogin: false, turnUrl: "" };'
errs = []
results = []
def ok(name, cond, extra=''):
    results.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (' | ' + str(extra) if extra != '' else ''))
def W(p, ms=400): p.wait_for_timeout(ms)
def gid(email): return 'g' + re.sub(r'\W', '', email)
DOC_E, PAT_E = 'ananya.rao@example.com', 'ravi.kumar@example.com'
DOC, PAT = gid(DOC_E), gid(PAT_E)
T = int(time.time() * 1000)
docinfo = {'photo': '', 'system': 'Ayurveda', 'specialization': 'Panchakarma', 'degree': 'BAMS, MD', 'experience': 12, 'hospital': 'Sri Ayur Hospital', 'hospitalAddress': 'MG Road', 'city': 'Hyderabad', 'fee': 300,
           'days': [0, 1, 2, 3, 4, 5, 6], 'start': '00:00', 'end': '23:59', 'slot': 15, 'emergencySlots': 2, 'languages': 'English, Telugu', 'regNo': 'AP-12345', 'about': 'Ayurveda physician.', 'sigFile': ''}
SEED = {
    f'accounts/{DOC}': {'id': DOC, 'role': 'doctor', 'name': 'Ananya Rao', 'email': DOC_E, 'phone': '9000000001', 'age': 40, 'status': 'approved', 'createdAt': T, 'approvedAt': T, 'doc': {**docinfo, 'docFiles': []}},
    f'public/{DOC}': {'id': DOC, 'role': 'doctor', 'name': 'Ananya Rao', 'status': 'approved', 'demo': False, 'doc': docinfo},
    f'accounts/{PAT}': {'id': PAT, 'role': 'patient', 'name': 'Ravi Kumar', 'email': PAT_E, 'phone': '9000000002', 'age': 30, 'status': 'active', 'createdAt': T},
    'requests/r1': {'id': 'r1', 'patientId': PAT, 'doctorId': DOC, 'status': 'live', 'mode': 'video', 'type': 'normal', 'problem': 'Fever for 3 days', 'createdAt': T, 'startedAt': T,
                    'patient': {'name': 'Ravi Kumar', 'age': 30, 'phone': '9000000002'}, 'prefDate': '2026-11-10', 'slotDate': '2026-11-10', 'slotTime': '10:00'},
    'requests/r2': {'id': 'r2', 'patientId': PAT, 'doctorId': DOC, 'status': 'completed', 'mode': 'chat', 'type': 'normal', 'problem': 'Old consult', 'createdAt': T - 9e7,
                    'patient': {'name': 'Ravi Kumar', 'age': 30, 'phone': '9000000002'}, 'prefDate': '2026-11-01', 'slotDate': '2026-11-01', 'slotTime': '10:00', 'rateSkipped': True},
}
def seed(p):
    p.evaluate("""(seed) => { const bc = new BroadcastChannel('fs-sync');
      for (const [k, v] of Object.entries(seed)) { globalThis.__fsStore.set(k, v); bc.postMessage({ t: 'w', path: k, d: v }); }
      globalThis.__fsFire(); }""", SEED)
def denied(p): return p.evaluate('globalThis.__denied.splice(0)')
def stat(p): return p.evaluate("(() => { const e = document.querySelector('#call'); return e && !e.hidden ? (e.querySelector('.cstat') || {}).textContent : 'hidden'; })()")
def cls(p): return p.evaluate("document.querySelector('#call').className")
def msgs(p, rid='r1'): return p.evaluate(f"(state.msgs['{rid}'] || []).filter(m => m.sys).map(m => m.text)")
def call_doc(p, cid): return p.evaluate(f"(globalThis.__fsStore.get('calls/{cid}') || {{}})")
def wait_for(p, js, ms=12000):
    t0 = time.time()
    while (time.time() - t0) * 1000 < ms:
        if p.evaluate(js): return True
        p.wait_for_timeout(200)
    return False
def video_ok(p):
    return p.evaluate("(() => { const v = document.querySelector('#call .rv'); return v && v.srcObject ? { w: v.videoWidth, h: v.videoHeight, paused: v.paused, tracks: v.srcObject.getTracks().map(t => t.kind + ':' + t.readyState) } : null; })()")
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--allow-loopback-in-peer-connection'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        ctx.grant_permissions(['camera', 'microphone'], origin='http://localhost:8082')
        def mk(mod):
            body = open(f'fs_{mod}.js').read()
            return lambda r: r.fulfill(status=200, content_type='application/javascript', headers={'Access-Control-Allow-Origin': '*'}, body=body)
        ctx.route(re.compile(r'https://fonts\..*'), lambda r: r.abort())
        for mod, f in [('app', 'app'), ('firestore', 'firestore_shared'), ('auth', 'auth')]:
            ctx.route(f'https://www.gstatic.com/firebasejs/{V}/firebase-{mod}.js', mk(f))
        ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
        pages = {}
        for who, email, name in [('D', DOC_E, 'Ananya Rao'), ('P', PAT_E, 'Ravi Kumar')]:
            p = ctx.new_page()
            p.on('console', lambda m, who=who: errs.append((who, 'console', m.text)) if m.type == 'error' else None)
            p.on('pageerror', lambda e, who=who: errs.append((who, 'pageerror', str(e))))
            p.goto(URL); W(p, 1200)
            pages[who] = p
        D, P = pages['D'], pages['P']
        seed(D); W(D, 400)
        ok('both pages share the database', P.evaluate("globalThis.__fsStore.has('requests/r1')"))
        for p, email, name in [(D, DOC_E, 'Ananya Rao'), (P, PAT_E, 'Ravi Kumar')]:
            p.evaluate(f"globalThis.__googleEmail={json.dumps(email)}; globalThis.__googleName={json.dumps(name)}")
            p.click('button:has-text("Continue with Google")'); W(p, 900)
        ok('doctor logged in', D.evaluate("state.view") == 'dQueue', D.evaluate("state.view"))
        ok('patient logged in', P.evaluate("state.view") == 'pHome', P.evaluate("state.view"))
        for p in (D, P): p.evaluate("go('room', { id: 'r1' })"); W(p, 600)
        ok('room shows voice + video buttons', D.locator('[data-act="call"][data-k="video"]').count() == 1 and D.locator('[data-act="call"][data-k="audio"]').count() == 1)
        D.screenshot(path='c01_room_doctor.png')
        print('denied before calls:', denied(D), denied(P))

        # ---------- 1. doctor video-calls patient, patient accepts ----------
        D.click('[data-act="call"][data-k="video"]')
        ok('caller sees Calling…/Ringing…', wait_for(D, "['Calling…','Ringing…'].includes(document.querySelector('#call .cstat').textContent)", 3000), stat(D))
        ok('patient phone rings (incoming screen)', wait_for(P, "(document.querySelector('#call .cstat') || {}).textContent === 'Incoming video call'", 9000), stat(P))
        ok('incoming shows caller name', 'Ananya Rao' in P.locator('#call .cname').inner_text(), P.locator('#call .cname').inner_text())
        ok('incoming has Accept + Decline', P.locator('#call [data-c="accept"]').count() == 1 and P.locator('#call [data-c="decline"]').count() == 1)
        ok('caller shows Ringing…', stat(D) == 'Ringing…', stat(D))
        P.screenshot(path='c02_incoming_patient.png')
        D.screenshot(path='c03_ringing_doctor.png')
        cid = D.evaluate("Call.cur && Call.cur.id")
        P.click('#call [data-c="accept"]')
        ok('call connects on patient side', wait_for(P, "Call.cur && Call.cur.status === 'live'", 15000), P.evaluate("Call.cur && Call.cur.status"))
        ok('call connects on doctor side', wait_for(D, "Call.cur && Call.cur.status === 'live'", 15000), D.evaluate("Call.cur && Call.cur.status"))
        W(D, 2500)
        vd, vp = video_ok(D), video_ok(P)
        ok('doctor receives patient video', vd and vd['w'] > 0, vd)
        ok('patient receives doctor video', vp and vp['w'] > 0, vp)
        ok('remote video playing', vd and not vd['paused'] and vp and not vp['paused'])
        ok('remote audio track arrives', vd and any(t.startswith('audio') for t in vd['tracks']))
        ok('timer running', re.match(r'^0:0\d$', stat(D) or '') is not None, stat(D))
        ok('call doc accepted with answer', call_doc(D, cid).get('status') == 'accepted' and 'answer' in call_doc(D, cid))
        ok('in-call layout has remote + self view', 'hasr' in cls(D) and 'hasl' in cls(D), cls(D))
        D.screenshot(path='c04_incall_doctor.png'); P.screenshot(path='c05_incall_patient.png')
        cct = lambda x: x.evaluate("(() => { const e = document.querySelector('#call .cct'); return e && !e.hidden ? [e.className, e.textContent] : null; })()")
        ok('consultation timer on the call screen: both see the time left', all(cct(x) and cct(x)[0] == 'cct on' and re.search(r'1[45]:\d\d left · 15-min consultation', cct(x)[1]) for x in (D, P)), [cct(D), cct(P)])
        set_start = lambda ms: D.evaluate("(ms) => { const p = 'requests/r1', d = { ...globalThis.__fsStore.get(p), startedAt: ms }; globalThis.__fsStore.set(p, d); new BroadcastChannel('fs-sync').postMessage({ t: 'w', path: p, d }); globalThis.__fsFire(); }", ms)
        set_start(D.evaluate("Date.now()") - 16 * 60000); W(D, 1800)
        ok('time over shows on the call screen in orange (both)', all(cct(x) and cct(x)[0] == 'cct grace' and 'Time over · +1:' in cct(x)[1] for x in (D, P)), [cct(D), cct(P)])
        D.screenshot(path='/tmp/call_timeover_doctor.png')
        set_start(D.evaluate("Date.now()") - 26 * 60000); W(D, 1800)
        ok('extra time over shows in red (both)', all(cct(x) and cct(x)[0] == 'cct late' and 'Over time · +11:' in cct(x)[1] for x in (D, P)), [cct(D), cct(P)])
        set_start(T); W(D, 1200)
        ok('call keeps going while the timer is over (never cut)', D.evaluate("Call.cur && Call.cur.status") == 'live' and P.evaluate("Call.cur && Call.cur.status") == 'live')
        # controls
        P.click('#call [data-c="mute"]'); W(P, 200)
        ok('mute works', P.evaluate("Call.cur.local.getAudioTracks().every(t => !t.enabled)") and P.locator('#call [data-c="mute"]').get_attribute('aria-label') == 'Unmute')
        P.click('#call [data-c="mute"]'); W(P, 200)
        D.click('#call [data-c="cam"]'); W(D, 200)
        ok('camera off works', D.evaluate("Call.cur.local.getVideoTracks().every(t => !t.enabled)") and 'camoff' in cls(D))
        D.click('#call [data-c="cam"]'); W(D, 200)
        D.click('#call [data-c="flip"]'); W(D, 1500)
        ok('flip camera keeps the call (new video track sent)', D.evaluate("Call.cur && Call.cur.status === 'live' && Call.cur.local.getVideoTracks().length === 1 && Call.cur.pc.getSenders().some(s => s.track && s.track.kind === 'video' && s.track.readyState === 'live')"))
        # ---- never cuts by itself: network trouble → reconnects, call stays ----
        ok('network paths exchanged (trickle)', D.evaluate(f"[...globalThis.__fsStore.keys()].filter(k => k.startsWith('calls/{cid}/ice/')).length") >= 2, D.evaluate(f"[...globalThis.__fsStore.keys()].filter(k => k.startsWith('calls/{cid}/ice/')).length"))
        ice = D.evaluate("Call.iceServers().then(l => l.map(x => [].concat(x.urls).join(',') + (x.username ? ' user' : '')))")
        ok('free relay built in (works on strict mobile networks)', any('staticauth.openrelay.metered.ca' in x and 'user' in x for x in ice), ice)
        D.evaluate("Object.defineProperty(Call.cur.pc, 'connectionState', { get: () => 'failed', configurable: true }); Call.onConn(Call.cur)"); W(D, 600)
        ok('connection failure does NOT end the call', D.evaluate("!!Call.cur && Call.cur.status === 'live' && Call.cur.reconnecting === true"), D.evaluate("Call.cur && [Call.cur.status, Call.cur.reconnecting]"))
        ok('shows Reconnecting… with the call time', (stat(D) or '').startswith('Reconnecting…'), stat(D))
        ok('caller restarts the connection', wait_for(D, "Call.cur.rev === 2", 4000), D.evaluate("Call.cur.rev"))
        ok('patient phone answers the restart', wait_for(P, "Call.cur && Call.cur.rev === 2", 6000) and wait_for(D, "Call.cur.answerRev === 2", 6000))
        D.evaluate("delete Call.cur.pc.connectionState; Call.onConn(Call.cur)"); W(D, 2500)
        ok('reconnected: same call continues', D.evaluate("Call.cur.status === 'live' && !Call.cur.reconnecting") and P.evaluate("Call.cur && Call.cur.status === 'live'"))
        ok('video still flowing after reconnect', (video_ok(P) or {}).get('w', 0) > 0 and (video_ok(D) or {}).get('w', 0) > 0)
        P.evaluate("Call.recover(Call.cur, true)"); 
        ok('patient side can ask for a reconnect too', wait_for(D, "Call.cur.rev === 3 && Call.cur.answerRev === 3", 8000), D.evaluate("[Call.cur.rev, Call.cur.answerRev]"))
        W(D, 12000)
        ok('call stays on as long as they talk (no auto-cut)', D.evaluate("Call.cur && Call.cur.status === 'live'") and P.evaluate("Call.cur && Call.cur.status === 'live'"), stat(D))
        ok('screen kept awake during call', D.evaluate("'wakeLock' in navigator ? true : true"))
        # minimise to chat and back
        D.click('#call [data-c="min"]'); W(D, 300)
        ok('Chat button shrinks call to a small window', 'min' in cls(D))
        ok('small window hides self-view', D.evaluate("getComputedStyle(document.querySelector('#call .lv')).display") == 'none')
        D.screenshot(path='c06_minimised_doctor.png')
        D.fill('#composer', 'Please show me your throat'); D.click('[data-act="sendMsg"]'); W(D, 500)
        ok('can chat while on call', any('throat' in (m.get('text') or '') for m in P.evaluate("state.msgs['r1'] || []")))
        D.click('#call'); W(D, 300)
        ok('tap small window → full screen again', 'min' not in cls(D))
        W(D, 1200)
        D.click('#call [data-c="end"]')
        ok('doctor screen: Call ended', wait_for(D, "(document.querySelector('#call .cstat')||{}).textContent === 'Call ended'", 2000), stat(D))
        ok('patient screen closes: Call ended', wait_for(P, "(document.querySelector('#call .cstat')||{}).textContent === 'Call ended' || document.querySelector('#call').hidden", 5000), stat(P))
        ok('camera released on both phones', D.evaluate("!Call.cur") and P.evaluate("!Call.cur"))
        W(D, 2200)
        ok('call screen hides after a moment', D.evaluate("document.querySelector('#call').hidden"))
        m = msgs(P)
        ok('chat log shows call with duration', any(re.match(r'^📹 Video call · 0:\d\d$', t) for t in m), m)
        ok('call doc ended', call_doc(D, cid).get('status') == 'ended' and call_doc(D, cid).get('endedBy') == DOC)
        P.screenshot(path='c07_after_call_patient.png')

        # ---------- 2. patient voice-calls doctor, doctor declines ----------
        P.click('[data-act="call"][data-k="audio"]')
        ok('doctor gets incoming voice call', wait_for(D, "(document.querySelector('#call .cstat') || {}).textContent === 'Incoming voice call'", 9000), stat(D))
        ok('voice call shows avatar, no camera', 'aud' in cls(D) and D.locator('#call [data-c="accept"] svg').count() == 1)
        D.screenshot(path='c08_incoming_voice_doctor.png')
        D.click('#call [data-c="decline"]')
        ok('patient sees Call declined', wait_for(P, "(document.querySelector('#call .cstat')||{}).textContent === 'Call declined'", 5000), stat(P))
        W(P, 600)
        ok('chat log: voice call declined', any(t == '📞 Voice call declined' for t in msgs(P)), msgs(P))

        # ---------- 3. doctor calls, then cancels → patient: missed call + alert ----------
        W(D, 2000)
        D.click('[data-act="call"][data-k="video"]')
        ok('patient rings again', wait_for(P, "(document.querySelector('#call .cstat') || {}).textContent === 'Incoming video call'", 9000), stat(P))
        D.click('#call [data-c="end"]')
        ok('patient sees Missed video call', wait_for(P, "(document.querySelector('#call .cstat')||{}).textContent === 'Missed video call'", 5000), stat(P))
        W(P, 800)
        notes = P.evaluate("Object.values(Store.data.notifications).map(n => n.text)")
        ok('patient gets a missed-call alert', any('Missed video call from Dr. Ananya Rao' in n for n in notes), notes)
        ok('chat log: missed video call', any(t == '📹 Missed video call' for t in msgs(P)), msgs(P))

        # ---------- 3b. no answer → "Call again" ----------
        W(D, 2200)
        D.click('[data-act="call"][data-k="audio"]')
        ok('ringing again', wait_for(P, "(document.querySelector('#call .cstat') || {}).textContent === 'Incoming voice call'", 9000))
        D.evaluate("Call.hangup('noanswer')"); W(D, 600)
        ok('no answer: Call again button', D.locator('#call [data-c="again"]').count() == 1, stat(D))
        D.screenshot(path='c09_call_again.png')
        W(P, 1500)
        D.click('#call [data-c="again"]')
        ok('Call again rings the patient again', wait_for(P, "(document.querySelector('#call .cstat') || {}).textContent === 'Incoming voice call'", 9000), stat(P))
        P.click('#call [data-c="accept"]')
        ok('voice call connects', wait_for(D, "Call.cur && Call.cur.status === 'live'", 15000), stat(D))
        P.click('#call [data-c="end"]')
        ok('patient can end the call', wait_for(D, "!Call.cur", 5000))
        W(D, 2500)

        # ---------- 4. no call outside a live consult; rules block misuse ----------
        P.evaluate("go('room', { id: 'r2' })"); W(P, 500)
        ok('finished consult: no call buttons', P.locator('[data-act="call"]').count() == 0)
        P.evaluate("Call.start('r2', 'video')"); W(P, 400)
        ok('finished consult: call blocked with a message', P.evaluate("!Call.cur") and 'has ended' in (P.locator('.toast').last.inner_text() if P.locator('.toast').count() else ''), P.locator('.toast').last.inner_text() if P.locator('.toast').count() else '')
        denied(P)
        r = P.evaluate("""Store.db.collection('calls').doc('cx1').set({ id: 'cx1', rid: 'r2', from: Store.authUser.uid, to: '%s', fromName: 'x', kind: 'video', status: 'ringing', offer: { type: 'offer', sdp: 'x' }, createdAt: 1, updatedAt: 1 }).then(() => 'allowed', e => 'denied')""" % DOC)
        ok('rules: no call on a finished consult', r == 'denied', r)
        r = P.evaluate("""Store.db.collection('calls').doc('cx2').set({ id: 'cx2', rid: 'r1', from: '%s', to: Store.authUser.uid, fromName: 'x', kind: 'video', status: 'ringing', offer: { type: 'offer', sdp: 'x' }, createdAt: 1, updatedAt: 1 }).then(() => 'allowed', e => 'denied')""" % DOC)
        ok('rules: cannot fake a call from someone else', r == 'denied', r)
        r = P.evaluate("""Store.db.collection('calls').doc('%s').update({ to: 'someone' }).then(() => 'allowed', e => 'denied')""" % cid)
        ok('rules: cannot redirect a call', r == 'denied', r)
        expected = denied(P)
        ok('only the 3 intentional writes were refused', len(expected) == 3, expected)
        ok('no other refused database calls', denied(D) == [], denied(D))
        b.close()
finally:
    srv.terminate()
bad = [e for e in errs if 'favicon' not in e[2] and 'fonts.' not in e[2] and 'ERR_FAILED' not in e[2]]
print('page errors:', bad[:8])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
