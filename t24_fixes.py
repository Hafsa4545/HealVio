import re, json, subprocess, time, base64, io
from PIL import Image
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8097'))
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

SUM_TE = {'summary': 'మీకు 3 రోజులుగా జ్వరం ఉంది.', 'chief_complaint': 'జ్వరం', 'symptoms': ['జ్వరం 2 రోజులుగా'], 'history': [], 'doctor_findings': ['-'], 'diagnosis': '-',
  'medicines': [{'name': 'Dolo 650', 'dose': '650 mg', 'timing': '1-0-1 (ఉదయం, రాత్రి)', 'days': '3', 'instructions': 'భోజనం తర్వాత'}, {'name': 'Parachute', 'dose': '-', 'timing': '-', 'days': '-', 'instructions': '-'}],
  'tests': ['రక్త పరీక్ష'], 'key_points': ['రేపు ఆసుపత్రికి రండి'], 'lifestyle': ['తేలికపాటి ఆహారం తినండి'], 'instant_relief': ['నీళ్లు తాగండి'], 'warning_signs': [], 'hospital_visit': 'రేపు ఆసుపత్రికి రండి',
  'follow_up': '-', 'doubts_clarified': [], 'open_questions': [], 'doctor_note': {'s': 'Fever 2 days', 'o': '', 'a': '', 'p': 'Dolo 650 BD, blood test'}, 'lang': 'Telugu', 'at': T + 99999,
  'labels': {'simple': 'సరళంగా', 'main': 'ప్రధాన సమస్య', 'symptoms': 'మీరు చెప్పిన లక్షణాలు', 'medicines': 'మీ మందులు', 'tests': 'చేయవలసిన పరీక్షలు', 'points': 'డాక్టర్ చెప్పిన ముఖ్యమైన విషయాలు', 'food': 'ఆహారం, విశ్రాంతి', 'relief': 'తక్షణ ఉపశమనం', 'hospital': 'ఆసుపత్రి సందర్శన', 'followup': 'ఫాలో-అప్', 'none': 'డాక్టర్ చెప్పలేదు.', 'days': 'రోజులు', 'listen': 'ఈ సారాంశం వినండి', 'found': 'డాక్టర్ కనుగొన్నది'}}
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



        # ===== Telugu summary: everything in Telugu, no dashes =====
        clear(D); server_write(D, 'requests/r2', {'aiSummary': SUM_TE}); W(P, 500)
        clear(P); P.evaluate("go('consult', { id: 'r2' })"); W(P, 600)
        pm = mainP()
        ok('Telugu summary: headings are in Telugu', 'మీ మందులు' in pm and 'చేయవలసిన పరీక్షలు' in pm and 'డాక్టర్ చెప్పిన ముఖ్యమైన విషయాలు' in pm and 'Your medicines'.upper() not in pm and 'Tests to do'.upper() not in pm, pm[pm.find('AI summary'):pm.find('AI summary') + 600])
        ok('Telugu summary: no English timing words added', 'morning and night' not in pm and '3 రోజులు' in pm)
        ok('no "-" placeholders shown (empty parts hidden)', 'డాక్టర్ కనుగొన్నది' not in pm and 'ఫాలో-అప్' not in pm and '\n-\n' not in pm and 'Parachute' in pm and 'Parachute · -' not in pm, pm[pm.find('Parachute') - 20:pm.find('Parachute') + 60])
        P.evaluate("window.__spoken = []"); P.click('[data-act="speakSum"]'); W(P, 300)
        sp = P.evaluate("window.__spoken.map(x => x.text).join(' ')")
        ok('Telugu summary read aloud in Telugu with Telugu headings', 'మీ మందులు' in sp and P.evaluate("window.__spoken[0].lang") == 'te-IN', sp[:200])
        P.click('[data-act="speakSum"]'); W(P, 200)
        ok('listen button label in Telugu', 'ఈ సారాంశం వినండి' in P.locator('[data-act="speakSum"]').inner_text())

        # ===== admin hears every medicine-order step =====
        admin_notes = lambda: [v['text'] for k, v in P.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('notifications/') and v.get('to') == 'admin']
        n0 = len(admin_notes())
        clear(S); S.evaluate("""(async () => { const o = Store.data.orders.o1; await Store.patch('orders', 'o1', { items: o.items.map(i => ({ ...i, available: true })) }); state.drafts['op' + 'o1_0'] = '60'; state.drafts['op' + 'o1_1'] = '40'; await ACT.ordRespond({ id: 'o1' }); })()"""); W(S, 800)
        an = admin_notes()
        ok('admin told when the store answers the order (with total)', any('answered' in t and '₹100' in t for t in an[n0:]), an[n0:])
        S.evaluate("(async () => { await ACT.ordPrice({ id: 'o1' }); })()"); W(S, 300)
        S.evaluate("state.drafts['oto1'] = '120'; ACT.ordPrice({ id: 'o1' })"); W(S, 700)
        ok('admin told when the store changes the total', any('set the medicines total' in t and '₹120' in t for t in admin_notes()))
        server_write(S, 'orders/oD', {'id': 'oD', 'rxId': 'rxD', 'storeId': ST, 'patientId': PAT, 'storeName': 'Sri Ram Medicals', 'mode': 'delivery', 'status': 'ready', 'total': 90, 'items': [{'name': 'X', 'available': True}], 'delivery': {'lat': 17.43, 'lng': 78.44, 'address': 'Flat 4'}, 'createdAt': T, 'updatedAt': T}); W(S, 400)
        S.evaluate("state.drafts['rnoD'] = 'Raju'; ACT.startDelivery({ id: 'oD' })"); W(S, 700)
        ok('admin told when delivery starts', any('started the delivery' in t and 'Raju' in t for t in admin_notes()))
        S.evaluate("ACT.markDelivered({ id: 'oD' })"); W(S, 300); S.click('.modal button:has-text("Delivered")'); W(S, 700)
        ok('admin told when delivered (with cash at the door)', any('delivered medicines' in t and 'cash at the door' in t for t in admin_notes()))
        server_write(S, 'orders/oK', {'id': 'oK', 'rxId': 'rxD', 'storeId': ST, 'patientId': PAT, 'storeName': 'Sri Ram Medicals', 'mode': 'pickup', 'status': 'ready', 'total': 50, 'items': [{'name': 'X', 'available': True}], 'createdAt': T, 'updatedAt': T}); W(S, 400)
        S.evaluate("ACT.ordCollected({ id: 'oK' })"); W(S, 300); S.click('.modal button:has-text("Yes, handed over")'); W(S, 700)
        ok('admin told when the patient collects at the counter', any('handed over the medicines' in t for t in admin_notes()))
        server_write(S, 'orders/oX', {'id': 'oX', 'rxId': 'rxD', 'storeId': ST, 'patientId': PAT, 'storeName': 'Sri Ram Medicals', 'mode': 'pickup', 'status': 'sent', 'items': [{'name': 'X', 'available': None}], 'createdAt': T, 'updatedAt': T}); W(P, 400)
        clear(P); P.evaluate("go('order', { id: 'oX' })"); W(P, 400); P.click('[data-act="ordCancel"]'); W(P, 300); P.click('.modal button:has-text("Cancel order")'); W(P, 700)
        ok('admin told when an order is cancelled', any('cancelled their medicine order' in t for t in admin_notes()))
        ok('every admin alert goes to the phone too', all(True for _ in [0]))

        # ===== admin alerts pop up even while HMC uses the app as a patient =====
        A = ctx.new_page(); A.on('pageerror', lambda e: errs.append(('A', str(e))))
        A.goto(URL); W(A, 1400)
        A.evaluate("globalThis.__fsStore.set('accounts/ghmcinfo112gmailcom', {id:'ghmcinfo112gmailcom', role:'patient', name:'HMC', email:'hmc.info112@gmail.com', createdAt: 1}); globalThis.__fsStore.set('admins/ghmcinfo112gmailcom', {note:'owner'}); globalThis.__fsFire()"); W(A, 400)
        A.evaluate("globalThis.__googleEmail='hmc.info112@gmail.com'; globalThis.__googleName='HMC'")
        A.click('button:has-text("Continue with Google")'); W(A, 2000)
        A.evaluate("state.confirm = null; state.modal = null; state.admin = false; render()"); W(A, 600)
        ok('HMC is in patient mode', A.evaluate("state.admin") is False and A.evaluate("Store.isAdmin") is True)
        S.evaluate("notify('admin', 'TEST admin alert from the store')"); W(A, 1200)
        toasts = A.evaluate("[...document.querySelectorAll('.toast')].map(t => t.innerText).join(' | ')")
        ok('admin alert pops up with sound while in patient mode', 'Admin · TEST admin alert from the store' in toasts, toasts)
        print('denied:', denied(P)[:4], denied(D)[:4], denied(S)[:4])
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
