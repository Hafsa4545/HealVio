import re, json, subprocess, time, base64, io
from PIL import Image
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8094'))
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
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, geolocation=HOME, permissions=['geolocation'])
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

        # ===== 1. REFUNDS =====
        P.evaluate("go('consult', { id: 'rA' })"); W(P, 500)
        ok('paid accepted visit: patient sees "Cancel & get a full refund"', P.locator('[data-act="cancelPaid"]').count() == 1)
        P.click('[data-act="cancelPaid"]'); W(P, 300)
        P.click('.modal button:has-text("Cancel & refund")'); W(P, 900)
        ok('refund asked from the server (signed in)', refund_log and refund_log[-1]['b']['kind'] == 'fee' and refund_log[-1]['b']['id'] == 'rA' and refund_log[-1]['auth'].startswith('Bearer '), refund_log[-1:])
        server_write(D, 'requests/rA', {'status': 'cancelled', 'refund': {'id': 'RF1', 'status': 'COMPLETED', 'amount': '3.16', 'currency': 'USD', 'inr': 300, 'at': T + 500, 'by': 'patient', 'reason': 'Cancelled by the patient'}}); W(P, 500)
        P.evaluate("render()"); W(P, 200)
        ok('patient sees "Refunded ₹300 to PayPal"', 'Refunded ₹300 to PayPal' in mainP(), mainP()[:400])
        ok('doctor told about the refund', any('fee was refunded' in t for t in notes_to(DOC)))
        ok('patient cannot cancel a paid visit without the refund (rules)', try_write(P, 'requests/rB', {'status': 'cancelled'}) == 'denied' if P.evaluate("!!Store.data.requests.rB") else True)
        # unpaid accepted → patient cancel allowed
        ok('patient can cancel an unpaid accepted visit', try_write(P, 'requests/rU', {'status': 'cancelled', 'closedAt': T}) == 'allowed')
        # doctor cancel of a paid visit must use the refund path
        server_write(D, 'requests/rP', {**SEED['requests/rA'], 'id': 'rP', 'status': 'accepted', 'paid': SEED['requests/rA']['paid']}); W(D, 400)
        ok("doctor can't reject a paid visit without refunding (rules)", try_write(D, 'requests/rP', {'status': 'rejected'}) == 'denied')
        D.evaluate("go('consult', { id: 'rP' })"); W(D, 500)
        ok('doctor sees "Cancel appointment & refund the patient"', D.locator('[data-act="docCancel"]:has-text("refund the patient")').count() == 1)
        D.click('[data-act="docCancel"]'); W(D, 300); D.fill('.modal textarea', 'I am unwell today'); D.click('.modal button:has-text("Cancel appointment")'); W(D, 900)
        ok('doctor cancel → server refund with the reason', refund_log[-1]['b'] == {'kind': 'fee', 'id': 'rP', 'reason': 'I am unwell today'})
        ok('patient told: cancelled + refunded', any('I am unwell today. Your fee was refunded' in t for t in notes_to(PAT)))
        # order cancel
        server_write(S, 'orders/oC', {'id': 'oC', 'rxId': 'rxD', 'storeId': ST, 'patientId': PAT, 'storeName': 'Sri Ram Medicals', 'mode': 'pickup', 'status': 'sent', 'items': [{'name': 'X', 'available': None}], 'createdAt': T, 'updatedAt': T + 1})
        W(P, 400); P.evaluate("go('order', { id: 'oC' })"); W(P, 400)
        P.click('[data-act="ordCancel"]'); W(P, 300); P.click('.modal button:has-text("Cancel order")'); W(P, 600)
        ok('patient cancels an unpaid order', P.evaluate("globalThis.__fsStore.get('orders/oC').status") == 'cancelled' and 'Order cancelled' in mainP())
        server_write(S, 'orders/oP', {'id': 'oP', 'rxId': 'rxD', 'storeId': ST, 'patientId': PAT, 'storeName': 'Sri Ram Medicals', 'mode': 'delivery', 'status': 'ready', 'total': 125, 'items': [{'name': 'X', 'available': True}], 'paid': {'by': 'paypal', 'captureId': 'CAP9', 'inr': 125, 'amount': '1.32', 'currency': 'USD', 'at': T}, 'createdAt': T, 'updatedAt': T + 2})
        W(S, 400)
        ok("store can't mark a paid order unavailable without refunding (rules)", try_write(S, 'orders/oP', {'status': 'unavailable'}) == 'denied')
        clear(S); S.evaluate("state.tab.so = 'active'; root('sOrders')"); W(S, 400)
        S.click('[data-act="ordCancel"][data-id="oP"]'); W(S, 300); S.fill('.modal textarea', 'Out of stock'); S.click('.modal button:has-text("Cancel & refund")'); W(S, 800)
        ok('store cancel of a paid order → server refund', refund_log[-1]['b'] == {'kind': 'order', 'id': 'oP', 'reason': 'Out of stock'})

        # ===== 2. READ ALOUD =====
        P.evaluate("go('rxView', { id: 'rxD' })"); W(P, 500)
        P.click('[data-act="speakRx"]'); W(P, 300)
        sp = P.evaluate("window.__spoken.map(x => x.text).join(' ')")
        ok('prescription read aloud with timings in words', 'Paracetamol, 650 mg, morning and night, for 5 days, after food' in sp and 'Dolo 650' in sp and 'only when needed' in sp, sp[:300])
        ok('button turns into Stop', P.locator('[data-act="speakRx"]:has-text("Stop")').count() == 1)
        P.click('[data-act="speakRx"]'); W(P, 200)
        ok('tap again stops reading', P.evaluate("window.__cancels") >= 2 and P.locator('[data-act="speakRx"]:has-text("Read my prescription")').count() == 1)
        P.evaluate("go('consult', { id: 'r2' })"); W(P, 500)
        P.evaluate("window.__spoken = []"); P.click('[data-act="speakSum"]'); W(P, 300)
        ok('AI summary can be listened to', 'You had fever for 3 days' in P.evaluate("window.__spoken.map(x => x.text).join(' ')") and P.evaluate("window.__spoken[0].lang") == 'en-IN')
        P.click('[data-act="speakSum"]'); W(P, 200)

        # ===== 3. REMINDERS =====
        P.evaluate("go('rxView', { id: 'rxD' })"); W(P, 500)
        ok('prescription page offers medicine reminders', P.locator('[data-act="sheet"][data-k="remind"]').count() == 1 and 'Get a phone alert at each dose time' in mainP())
        P.click('[data-act="sheet"][data-k="remind"]'); W(P, 400)
        sh = P.locator('.sheet').inner_text()
        ok('reminder sheet: times and each medicine', 'Morning' in sh and 'Night' in sh and 'Paracetamol' in sh and 'Cetirizine' in sh, sh[:300])
        on = P.evaluate("state.form.rem.items.map(i => [i.name, i.slots.join(''), i.days])")
        ok('timings picked from the prescription (1-0-1 → morning+night, SOS → none)', on == [['Paracetamol', 'mn', '5'], ['Cetirizine', 'n', '3'], ['Dolo 650', '', '5']], on)
        P.click('[data-act="remSlot"][data-i="1"][data-k="m"]'); W(P, 150)
        P.fill('#rm-t-n', '22:00')
        P.click('[data-act="remSave"]'); W(P, 800)
        rd = P.evaluate("globalThis.__fsStore.get('reminders/rem_rxD')")
        ok('reminders saved for this patient only', rd and rd['uid'] == PAT and rd['on'] is True and rd['times']['n'] == '22:00' and len(rd['items']) == 2 and rd['items'][1]['slots'] == ['m', 'n'], rd and {k: rd[k] for k in ('uid', 'on', 'times')})
        ok('end date = today + days − 1, next time computed', rd['items'][0]['until'] == P.evaluate("remAddL(today(), 4)") and rd['nextAt'] > P.evaluate("Date.now()") and rd['tz'] == P.evaluate("new Date().getTimezoneOffset()"))
        ok('prescription page shows "On · next …"', 'On · next' in mainP())
        ok("other people can't see your reminders (rules)", D.evaluate("Store.db.collection('reminders').doc('rem_rxD').get().then(() => 'allowed', () => 'denied')") == 'denied')
        P.evaluate("root('pHome')"); W(P, 600)
        ok("home shows Today's medicines", "Today's medicines" in mainP() and 'Paracetamol 650 mg' in mainP())
        P.screenshot(path='f01_today.png')
        P.locator('[data-act="remTaken"]').first.click(); W(P, 500)
        tk = P.evaluate("globalThis.__fsStore.get('reminders/rem_rxD').taken")
        ok('tap Taken → saved', tk and any(v for v in tk.values()), tk)
        P.evaluate("go('rxView', { id: 'rxD' })"); W(P, 300); P.click('[data-act="sheet"][data-k="remind"]'); W(P, 300)
        P.click('[data-act="remOff"]'); W(P, 600)
        ok('turn off → stays off', P.evaluate("globalThis.__fsStore.get('reminders/rem_rxD').on") is False and 'Get a phone alert' in mainP())

        # ===== 4. AI: WHICH DOCTOR? =====
        P.evaluate("root('pHome')"); W(P, 400)
        ok('home has "Not sure which doctor you need?"', 'Not sure which doctor you need?' in mainP())
        P.fill('#fd-q', 'fever and body pain for 3 days'); P.click('[data-act="findDoctor"]'); W(P, 900)
        ok('AI suggests the kind of doctor + how soon + warning signs', 'General Physician · Allopathy' in mainP() and 'See a doctor soon' in mainP() and 'Fever above 103 F' in mainP(), mainP()[:600])
        ok('prompt lists the doctors in the app and forbids medicines', ai_log and 'NEVER suggest medicines' in ai_log[-1] and '(Allopathy)' in ai_log[-1])
        P.click('[data-act="finderShow"]'); W(P, 400)
        ok('"Show these doctors" filters the list', P.evaluate("state.filters.sys") == 'Allopathy' and P.evaluate("state.form.problem") == 'fever and body pain for 3 days')
        P.screenshot(path='f02_finder.png')
        ai_answer['v'] = {'specialization': 'Psychiatry', 'system': 'Allopathy', 'urgency': 'emergency', 'why': 'You need help right now.', 'warn': [], 'crisis': True}
        P.evaluate("state.filters.sys = 'All'; render()"); P.fill('#fd-q', 'I want to end my life'); P.click('[data-act="findDoctor"]'); W(P, 900)
        ok('emergency: Call 108 + Tele-MANAS 14416', P.locator('.sos a[href="tel:108"]').count() >= 1 and P.locator('.sos a[href="tel:14416"]').count() >= 1)

        # ===== 5. PAPER PRESCRIPTION =====
        buf = io.BytesIO(); Image.open('../face.png').convert('RGB').resize((900, 1200)).save(buf, 'JPEG', quality=85)
        open('/tmp/paper_rx.jpg', 'wb').write(buf.getvalue())
        P.evaluate("root('pStores')"); W(P, 300)
        P.click('[data-act="newOrder"]:has-text("Order medicines")'); W(P, 500)
        P.click('[data-act="ordPick"][data-k="rxId"][data-v="paper"]'); W(P, 300)
        ok('paper prescription option with a photo button', P.locator('input[type="file"][data-file="paperRx"]').count() == 1)
        P.set_input_files('input[type="file"][data-file="paperRx"]', '/tmp/paper_rx.jpg'); W(P, 1500)
        ok('photo sent to AI to read', read_log and read_log[-1].startswith('data:image/jpeg;base64,'))
        ok('AI-read medicines shown for checking', 'AI read these medicines' in mainP() and 'Augmentin 625 625 mg 1-0-1 5 days after food' in P.locator('#pp-text').input_value(), P.locator('#pp-text').input_value())
        P.fill('#pp-text', 'Augmentin 625 mg 1-0-1 5 days, Pan 40 mg 1-0-0 5 days, ORS'); W(P, 200)
        P.click('[data-act="ordPick"][data-k="mode"][data-v="pickup"]'); W(P, 200)
        P.click(f'[data-act="ordPick"][data-k="storeId"][data-v="{ST}"]'); W(P, 200)
        P.screenshot(path='f03_paper.png')
        P.click('[data-act="placeOrder"]'); W(P, 900)
        po = [v for k, v in P.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('orders/') and v.get('paperRx')]
        ok('paper order sent with the photo and 3 medicines', po and po[0]['rxId'] is None and [i['name'] for i in po[0]['items']] == ['Augmentin', 'Pan', 'ORS'] and po[0]['doctorName'] == 'Paper prescription', po and [i['name'] for i in po[0]['items']])
        ok('store alerted to check the photo', any('paper prescription photo' in t for t in notes_to(ST)))
        clear(S); S.evaluate("state.tab.so = 'new'; render()"); W(S, 500)
        ok('store sees the prescription photo', S.locator(f'img.paperimg[data-id="{po[0]["id"]}"]').count() == 1 and 'check the photo' in S.locator('main').inner_text().lower())
        S.click(f'img.paperimg[data-id="{po[0]["id"]}"]'); W(S, 300)
        ok('store can zoom the photo', S.locator('#zoom-ov img').count() == 1)
        S.click('#zoom-ov .zx'); W(S, 200)
        r = P.evaluate("""Store.db.collection('orders').doc('oFake').set({ id: 'oFake', rxId: null, paperRx: 'http://x', storeId: '%s', patientId: Store.authUser.uid, status: 'sent', items: [] }).then(() => 'allowed', () => 'denied')""" % ST)
        ok('only real photos accepted for paper orders (rules)', r == 'denied')

        # ===== 6. CALLS: relay fallback =====
        res = P.evaluate("""(async () => { const out = []; Call.ice = { exp: Date.now() + 1e6, list: [{ urls: ['stun:x'] }, { urls: ['turn:turn.cloudflare.com:3478?transport=udp', 'turns:turn.cloudflare.com:443?transport=tcp'], username: 'u', credential: 'c' }] };
          const c = { fixes: 0, pc: { setConfiguration(cfg) { out.push(cfg.iceTransportPolicy); } } };
          const L = Call.ice.list; const iceOrig = Call.iceServers; Call.iceServers = async () => L;
          await Call.useRelay(c); c.fixes = 1; await Call.useRelay(c); Call.iceServers = iceOrig; return [out, !!c.relay]; })()""")
        ok('first try: all routes; after a failure: relay only', res[0] == ['all', 'relay'] and res[1] is True, res)
        res2 = P.evaluate("""(async () => { const out = []; const c = { fixes: 1, pc: { setConfiguration(cfg) { out.push(cfg.iceTransportPolicy); } } };
          const o = Call.iceServers; Call.iceServers = async () => [{ urls: ['stun:x'] }]; await Call.useRelay(c); Call.iceServers = o; return out; })()""")
        ok('no relay server configured → keeps trying all routes', res2 == ['all'])
        res3 = P.evaluate("""(async () => { const out = []; const c = { fixes: 1, pc: { setConfiguration(cfg) { out.push(cfg.iceTransportPolicy); } } };
          const o = Call.iceServers; Call.iceServers = async () => [{ urls: ['stun:x'] }, ...(await Call.openRelay())]; await Call.useRelay(c); Call.iceServers = o; return out; })()""")
        ok('only the community relay → not forced (keeps every route open)', res3 == ['all'], res3)

        # ===== 7. ADMIN SYSTEM CHECK =====
        A = ctx.new_page(); A.on('pageerror', lambda e: errs.append(('A', str(e))))
        A.goto(URL); W(A, 1400)
        A.evaluate("globalThis.__fsStore.set('accounts/ghmcinfo112gmailcom', {id:'ghmcinfo112gmailcom', role:'patient', name:'HMC', email:'hmc.info112@gmail.com', createdAt: 1}); globalThis.__fsStore.set('admins/ghmcinfo112gmailcom', {note:'owner'}); globalThis.__fsFire()"); W(A, 400)
        A.evaluate("globalThis.__googleEmail='hmc.info112@gmail.com'; globalThis.__googleName='HMC'")
        A.click('button:has-text("Continue with Google")'); W(A, 1200)
        auid = A.evaluate("Store.authUser.uid")
        A.evaluate("globalThis.__fsStore.set('admins/%s', {note:'owner'}); globalThis.__fsStore.set('system/cron', {at: Date.now() - 3*60000, sent: 2}); globalThis.__fsFire()" % auid); W(A, 900)
        A.evaluate("state.confirm = null; state.modal = null; state.admin = true; LS.set('healvio:admin','1'); state.stack = []; state.view = 'aHome'; render()"); W(A, 900)
        am = A.locator('main').inner_text()
        ok('admin sees System check', 'System check' in am and 'AI notes & summary' in am, am[:300])
        ok('missing call relay key is flagged with the fix', 'Add TURN_USERNAME and TURN_PASSWORD (free from expressturn.com)' in am)
        ok('reminders cron shows last check', 'last check 3 min ago' in am, am[:900])
        ok('PayPal shows test mode', 'Working in test mode' in am)
        A.screenshot(path='f04_admin.png', full_page=False)
        ok('non-admin cannot read system status (rules)', P.evaluate("Store.db.collection('system').doc('cron').get().then(() => 'allowed', () => 'denied')") == 'denied')
        print('denied:', denied(P)[:3], denied(D)[:3], denied(S)[:3])
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
