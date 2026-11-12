import re, json, subprocess, time, base64, io
from PIL import Image
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8098'))
status.update({'refund': True, 'readRx': True, 'reminders': True, 'turn': False, 'summary': True})
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

sum_log, listen_log = [], []
SUMMARY = {'summary': 'You had fever for 3 days. The doctor said it is a viral fever.', 'chief_complaint': 'Fever for 3 days', 'symptoms': ['Fever for 3 days', 'Body pain'], 'history': [], 'doctor_findings': ['Throat is red'],
  'diagnosis': 'Viral fever', 'medicines': [{'name': 'Dolo 650', 'dose': '650 mg', 'timing': '1-0-1', 'days': '3', 'instructions': 'after food'}], 'tests': ['CBC blood test'], 'key_points': ['Drink plenty of water'],
  'lifestyle': ['Rest for 2 days'], 'instant_relief': ['Warm water gargle'], 'warning_signs': ['Fever above 103 F'], 'hospital_visit': '', 'follow_up': 'After 3 days', 'doubts_clarified': [], 'open_questions': [],
  'doctor_note': {'s': 'Fever 3 days', 'o': 'Throat red', 'a': 'Viral fever', 'p': 'Dolo 650 BD x3d, CBC'}, 'lang': 'English', 'at': T + 99999, 'lines': 42, 'steps': 2}
def summary_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    sum_log.append({'b': json.loads(route.request.post_data), 'auth': route.request.headers.get('authorization')})
    j(route, {'summary': SUMMARY})
def listen_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    listen_log.append(json.loads(route.request.post_data))
    j(route, {'text': 'I have a headache since morning.'})
REV = [('Sita Lakshmi', 5, 'Very patient doctor, explained everything clearly about my fever and medicines.', 3), ('Arjun Reddy', 5, 'Good', 10), ('Meena Kumari', 4, 'Helpful consultation, the prescription came quickly.', 20),
       ('Kiran Babu', 2, 'Doctor joined 20 minutes late and the call dropped twice.', 30), ('Lakshmi Devi', 5, '', 40), ('Ravi Teja', 3, 'Okay experience overall, could explain diet more.', 50), ('Anil', 1, '', 60)]
for i, (nm, st, tx, days) in enumerate(REV):
    SEED[f'reviews/rv{i}'] = {'id': f'rv{i}', 'doctorId': DOC, 'patientId': f'pp{i}', 'patientName': nm, 'rating': st, 'review': tx, 'ratedAt': T - days * 86400000}
SEED['reviews/rvP'] = {'id': 'rvP', 'doctorId': DOC, 'patientId': PAT, 'patientName': 'Ravi K.', 'rating': 4, 'review': 'Nice doctor, clear advice on medicines and diet.', 'ratedAt': T - 2 * 86400000}
SEED['requests/rQ'] = {**SEED['requests/rA'], 'id': 'rQ', 'status': 'requested', 'slotDate': None, 'slotTime': None, 'acceptedFor': None}
SEED['requests/rQ'].pop('paid', None)
SEED['orders/oN'] = {'id': 'oN', 'rxId': 'rxD', 'storeId': ST, 'patientId': PAT, 'storeName': 'Sri Ram Medicals', 'mode': 'delivery', 'status': 'out', 'total': 120, 'items': [{'name': 'X', 'available': True}],
                     'delivery': {'lat': 17.4375, 'lng': 78.4483, 'address': 'Flat 4, Ameerpet'}, 'createdAt': T, 'updatedAt': T}

SEED['public/doc2'] = {**SEED[f'public/{DOC}'], 'id': 'doc2', 'name': 'Kiran Rao'}
SEED['accounts/doc2'] = {**SEED[f'accounts/{DOC}'], 'id': 'doc2', 'name': 'Kiran Rao', 'email': 'kiran@example.com'}
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
        ctx.route('https://w.healvio.test/summary', summary_route)
        ctx.route('https://w.healvio.test/listen', listen_route)
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



        # ===== 1. CONSENT BEFORE AN ONLINE CONSULTATION =====
        clear(P); P.evaluate("go('pDoctor', { id: 'doc2' })"); W(P, 600)
        P.click('button:has-text("Request consult")'); W(P, 400)
        ok('request form has the consent tick with Terms and Privacy links', P.locator('#rq-consent').count() == 1 and P.locator('.consent a[href="terms.html"]').count() == 1 and 'online consultation' in P.locator('.consent').inner_text())
        P.fill('#rq-problem', 'Headache for 2 days'); P.click('.sheet button:has-text("Send request")'); W(P, 500)
        n_doc2 = lambda: len([k for k, v in P.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('requests/') and v.get('doctorId') == 'doc2'])
        ok('cannot send without agreeing', n_doc2() == 0 and 'tick the box' in P.locator('.sheet').inner_text())
        P.check('#rq-consent'); P.click('.sheet button:has-text("Send request")'); W(P, 800)
        rq = [v for k, v in P.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('requests/') and v.get('doctorId') == 'doc2']
        ok('after ticking, the request is sent with the consent saved', len(rq) == 1 and rq[0].get('consent') and rq[0]['consent']['v'] == 1 and rq[0]['consent']['at'] > 0, rq[:1])

        # ===== 2. REPORT A PROBLEM → ADMIN =====
        clear(P); P.evaluate("go('consult', { id: 'rA' })"); W(P, 500)
        ok('every consultation has "Report a problem"', P.locator('[data-k="report"]').count() == 1)
        P.click('[data-k="report"]'); W(P, 300)
        P.click('.sheet button:has-text("Send report")'); W(P, 300)
        ok('must choose a topic and write what happened', 'Choose what the problem is about' in P.locator('.sheet').inner_text())
        P.click('[data-act="setCmp"][data-v="doctor"]'); P.fill('#cmp-text', 'The doctor joined 30 minutes late and was rude.'); P.click('.sheet button:has-text("Send report")'); W(P, 900)
        cps = [v for k, v in P.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('complaints/')]
        ok('complaint saved for the admin (who, about whom, which consultation)', len(cps) == 1 and cps[0]['by'] == PAT and cps[0]['against'] == DOC and cps[0]['ref'] == {'kind': 'consult', 'id': 'rA'} and cps[0]['status'] == 'open', cps)
        an = [v for k, v in P.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('notifications/') and v.get('to') == 'admin' and 'New complaint' in v.get('text', '')]
        ok('admin alerted at once (urgent)', an and an[-1]['kind'] == 'urgent')
        cid = cps[0]['id']
        ok("the doctor can't read the patient's complaint (rules)", D.evaluate(f"Store.db.collection('complaints').doc('{cid}').get().then(() => 'allowed', () => 'denied')") == 'denied')
        ok("the patient can't write the admin's reply (rules)", P.evaluate(f"Store.db.collection('complaints').doc('{cid}').update({{ reply: 'fake', status: 'resolved' }}).then(() => 'allowed', () => 'denied')") == 'denied')
        P.evaluate("root('profile')"); W(P, 600)
        ok('patient sees the report in Profile → My reports (Open)', 'My reports' in mainP() and 'Doctor or consultation' in mainP())
        clear(S); S.evaluate("go('order', { id: 'o1' })"); W(S, 500)
        ok('medicine orders have "Report a problem" too', S.locator('[data-k="report"][data-type="order"]').count() == 1)
        A = ctx.new_page(); A.on('pageerror', lambda e: errs.append(('A', str(e))))
        A.goto(URL); W(A, 1400)
        A.evaluate("globalThis.__fsStore.set('accounts/ghmcinfo112gmailcom', {id:'ghmcinfo112gmailcom', role:'patient', name:'HMC', email:'hmc.info112@gmail.com', createdAt: 1}); globalThis.__fsStore.set('admins/ghmcinfo112gmailcom', {note:'owner'}); globalThis.__fsFire()"); W(A, 400)
        A.evaluate("globalThis.__googleEmail='hmc.info112@gmail.com'; globalThis.__googleName='HMC'")
        A.click('button:has-text("Continue with Google")'); W(A, 2000)
        A.evaluate("state.confirm = null; state.modal = null; state.admin = true; state.stack = []; state.view = 'aMore'; state.tabRoot = 'aMore'; render()"); W(A, 1000)
        am = A.locator('main').inner_text()
        ok('admin sees the complaint with who and about whom', 'Complaints' in am and 'joined 30 minutes late' in am and 'Ravi Kumar' in am and 'Dr. Ananya Rao' in am, am[:500])
        A.screenshot(path='h01_complaints.png')
        A.click(f'[data-act="cmpOpen"][data-id="{cid}"]'); W(A, 300)
        A.fill('#cmp-reply', 'Sorry! We spoke to the doctor and refunded your fee.'); A.click('[data-act="cmpResolve"]'); W(A, 900)
        cp = P.evaluate(f"globalThis.__fsStore.get('complaints/{cid}')")
        ok('admin reply closes the complaint', cp['status'] == 'resolved' and cp['reply'].startswith('Sorry!') and cp.get('resolvedAt'))
        ok('patient told about the reply', any('Healvio replied to your report' in t for t in notes_to(PAT)))
        P.evaluate("render()"); W(P, 600)
        ok('patient sees "Reply from Healvio" in My reports', 'Reply from Healvio' in mainP() and 'refunded your fee' in mainP())

        # ===== 3. TERMS OF USE =====
        t = P.evaluate("fetch('terms.html').then(r => r.text())")
        ok('Terms of Use page: platform role, doctor responsibility, AI limits, refunds, grievance, emergency', 'technology platform' in t and 'responsible for their medical decisions' in t and 'never diagnoses, prescribes' in t and 'Full refund' in t and 'Report a problem' in t and '108' in t)
        ok('Terms linked in Profile', P.locator('a[href="terms.html"]').count() >= 1)
        pv = P.evaluate("fetch('privacy.html').then(r => r.text())")
        ok('Privacy page is filled in: owner, city, email, grievance officer, no template box', 'Healvio (HMC), Bangalore, Karnataka' in pv and pv.count('hmc.info112@gmail.com') >= 3 and 'Grievance Officer: HMC' in pv and 'class="todo"' not in pv and 'Template' not in pv and '3 years' in pv and '[' not in pv)
        ok('Terms show operator and grievance times', 'Healvio (HMC), Bangalore' in t and '24 hours' in t and '15 days' in t)

        # ===== 4. LEGAL FOOTER ON PRESCRIPTIONS =====
        clear(P); P.evaluate("go('rxView', { id: 'rxD' })"); W(P, 600)
        lg = P.locator('.rxlegal').inner_text() if P.locator('.rxlegal').count() else ''
        ok('prescription shows the legal footer', 'Telemedicine Practice Guidelines, 2020' in lg and 'is responsible for this prescription' in lg and 'technology platform' in lg and 'online consultation' in lg, lg)
        reg = P.evaluate(f"(A('{DOC}').doc || {{}}).regNo || ''")
        ok('doctor registration number on the prescription', (not reg) or ('Reg. No. ' + reg) in P.locator('.rx').inner_text(), reg)
        ok('Homeopathy / Ayurveda prescriptions name their own guidelines', P.evaluate("RX_RULES.Homeopathy.includes('Homoeopathic') && RX_RULES.Ayurveda.includes('Ayurveda, Siddha & Unani')"))

        # ===== 5. MEDICINES NOT ALLOWED ONLINE =====
        server_write(D, 'requests/rA', {'status': 'live', 'startedAt': T, 'rxId': None}); W(D, 400)
        clear(D); D.evaluate("go('rxEdit', { id: 'rA' })"); W(D, 500)
        D.evaluate("state.form.rx.medicines = [{ name: 'Alprazolam 0.5 mg', dose: '1 tab', freq: '0-0-1', days: '5', note: '' }, { name: 'Paracetamol 650', dose: '1 tab', freq: '1-0-1', days: '3', note: '' }]; render()"); W(D, 300)
        ok('doctor warned while writing', "Schedule X / narcotic medicines can't be prescribed" in D.locator('main').inner_text())
        n_rx = lambda: len([k for k in P.evaluate("Object.keys(Object.fromEntries(globalThis.__fsStore))") if k.startswith('prescriptions/')])
        before = n_rx()
        D.evaluate("ACT.saveRx({ id: 'rA' })"); W(D, 600)
        ok('saving is blocked with a clear reason', n_rx() == before and "Alprazolam 0.5 mg can't be prescribed online" in D.locator('main').inner_text())
        ok('brand names and other banned medicines are caught too', D.evaluate("['Ultracet', 'Rivotril 0.5', 'Corex syrup', 'tramadol 50'].every(n => bannedMed(n, 'Allopathy'))"))
        ok('normal medicines are fine', D.evaluate("['Paracetamol 650', 'Dolo', 'Azithromycin 500', 'Cetirizine', 'Pan 40'].every(n => !bannedMed(n, 'Allopathy'))"))
        ok('homeopathy remedies with similar names are not blocked', D.evaluate("!bannedMed('Opium 30C', 'Homeopathy') && !bannedMed('Cannabis Indica 200', 'Homeopathy')"))
        D.evaluate("state.form.rx.medicines = state.form.rx.medicines.slice(1); state.err = ''; ACT.saveRx({ id: 'rA' })"); W(D, 900)
        ok('after removing it, the prescription saves', n_rx() == before + 1)
        print('denied:', denied(P)[:4], denied(D)[:4], denied(S)[:4])
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
