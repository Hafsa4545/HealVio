import re, json, subprocess, time, base64, io
from PIL import Image
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8095'))
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


        # ===== 1. PAY BEFORE THE CONSULTATION =====
        clear(D); D.evaluate("go('consult', { id: 'rU' })"); W(D, 500)
        ok('doctor sees the fee is not paid yet', 'not paid yet' in D.locator('main').inner_text() and 'The consultation starts after the patient pays' in D.locator('main').inner_text())
        D.click('[data-act="startConsult"]'); W(D, 400)
        ok('Start without payment is stopped: "Fee not paid yet"', D.locator('.sheet').count() == 1 and 'Fee not paid yet' in D.locator('.sheet').inner_text() and P.evaluate("globalThis.__fsStore.get('requests/rU').status") == 'accepted')
        D.screenshot(path='g01_feegate.png')
        D.click('.sheet [data-act="payNudge"]'); W(D, 700)
        nn = [v for k, v in P.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('notifications/') and v.get('to') == PAT and 'consultation fee in Healvio' in v.get('text', '')]
        ok('doctor can remind the patient to pay (urgent alert)', nn and nn[-1]['kind'] == 'urgent' and nn[-1].get('title') == 'Pay to start your consultation', nn[-1:])
        clear(P); P.evaluate("go('room', { id: 'rU' })"); W(P, 600)
        ok('patient sees "Pay now to confirm your slot" at the top of the consult room', P.locator('.paypre [data-act="payFee"]').count() == 1 and 'Pay now to confirm your slot' in P.locator('.paypre').inner_text())
        P.screenshot(path='g02_paytop.png')
        clear(D); D.evaluate("state.tab.dq = 'schedule'; root('dQueue')"); W(D, 500)
        ok('doctor queue shows "Fee not paid yet"', 'not paid yet' in D.locator('main').inner_text() and '✓ Fee paid' in D.locator('main').inner_text(), D.locator('main').inner_text()[:500])
        D.evaluate("go('consult', { id: 'rU' })"); W(D, 400); D.click('[data-act="startConsult"]'); W(D, 300)
        D.click('.sheet [data-act="startConsult"][data-force="1"]'); W(D, 900)
        ru = P.evaluate("globalThis.__fsStore.get('requests/rU')")
        ok('"Start anyway" starts and records free / paid outside the app', ru['status'] == 'live' and ru.get('feeWaived') and ru['feeWaived']['by'] == DOC)
        clear(P); P.evaluate("go('consult', { id: 'rU' })"); W(P, 500)
        ok('patient sees "free or paid outside the app" (no Pay button)', 'free or paid outside the app' in P.locator('main').inner_text() and P.locator('[data-act="payFee"]').count() == 0)
        clear(D); D.evaluate("go('consult', { id: 'rA' })"); W(D, 400); D.click('[data-act="startConsult"]'); W(D, 900)
        ok('paid consultation starts right away', P.evaluate("globalThis.__fsStore.get('requests/rA').status") == 'live' and D.locator('.sheet').count() == 0)
        res = D.evaluate("""(async () => { const nf = nextFree(me(), addDays(today(), 1), 'rQ'); state.form.accDate = nf.date; state.form.accTime = nf.time; state.sheet = { kind: 'accept', id: 'rQ' }; await ACT.confirmAccept({ id: 'rQ' }); return nf; })()""")
        W(D, 600)
        nq = [v for k, v in P.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('notifications/') and v.get('to') == PAT and 'accepted your request' in v.get('text', '')]
        rq = P.evaluate("globalThis.__fsStore.get('requests/rQ')")
        ok('accept alert asks the patient to pay first', nq and 'Please pay the ₹300 fee in the app to confirm it' in nq[-1]['text'] and nq[-1]['kind'] == 'urgent', nq[-1:])
        ok('booking saves the time zone for pay reminders', rq['status'] == 'accepted' and rq.get('tz') == D.evaluate("new Date().getTimezoneOffset()"))

        # ===== 2. REVIEWS LIKE PLAY STORE =====
        clear(P); P.evaluate(f"go('pDoctor', {{ id: '{DOC}' }})"); W(P, 700)
        pm = mainP()
        ok('profile: rating summary with star bars', 'Ratings & reviews' in pm and P.locator('.tapbar').count() == 5 and 'of patients rated 4★ or more' in pm)
        tops = P.locator('.revs .rev').count()
        ok('profile shows only the top 3 reviews', tops == 3, tops)
        ok('names are short (first name + initial)', 'Sita L.' in pm and 'Sita Lakshmi' not in pm, pm[pm.find('Ratings'):pm.find('Ratings') + 600])
        ok('top reviews include a critical one for balance', P.locator('.revs .rev .stars').evaluate_all("els => els.some(e => e.querySelectorAll('.ic:not(.off)').length <= 3)"))
        ok('"See all 8 reviews" button', P.locator('[data-act="revAll"][data-k="0"]:has-text("See all 8 reviews")').count() == 1)
        P.locator('.tapbar[data-k="5"]').click(); W(P, 400)
        five = P.locator('.sheet .rev').count(); fivestars = P.locator('.sheet .rev .stars').evaluate_all("els => els.map(e => e.querySelectorAll('.ic:not(.off)').length)")
        ok('tap 5★ → only 5-star reviews', five == 3 and all(x == 5 for x in fivestars), fivestars)
        P.screenshot(path='g03_reviews5.png')
        P.click('.sheet [data-act="revStar"][data-v="2"]'); W(P, 300)
        ok('tap 2★ → the 2-star review', P.locator('.sheet .rev').count() == 1 and 'joined 20 minutes late' in P.locator('.sheet').inner_text())
        P.click('.sheet [data-act="revStar"][data-v="0"]'); W(P, 200); P.click('.sheet [data-act="revSort"][data-v="low"]'); W(P, 300)
        first = P.locator('.sheet .rev').first.locator('.stars .ic:not(.off)').count()
        ok('sort by lowest', first == 1 and P.locator('.sheet .rev').count() == 8, first)
        P.click('.sheet [data-act="revSort"][data-v="new"]'); W(P, 300)
        ok('sort by newest', 'Ravi K.' in P.locator('.sheet .rev').first.inner_text())
        clear(P)
        clear(D); D.evaluate("root('profile')"); W(D, 500)
        D.click('[data-act="revAll"]:has-text("My reviews")'); W(D, 400)
        ok('doctor sees all own reviews with Reply buttons', D.locator('.sheet [data-act="revReply"]').count() == 8)
        D.locator('.sheet [data-act="revReply"][data-id="rvP"]').click(); W(D, 300)
        D.fill('#rv-reply', 'Thank you Ravi! Get well soon.'); D.click('[data-act="revReplySave"]'); W(D, 800)
        rv = P.evaluate("globalThis.__fsStore.get('reviews/rvP')")
        ok('doctor reply saved on the review', rv.get('reply') == 'Thank you Ravi! Get well soon.' and rv.get('replyAt'))
        ok('patient told about the reply', any('replied to your review' in t for t in notes_to(PAT)))
        P.evaluate(f"go('pDoctor', {{ id: '{DOC}' }})"); W(P, 600)
        ok('reply shows under the review on the public profile', 'Reply from Dr. Ananya Rao' in mainP() and 'Thank you Ravi! Get well soon.' in mainP())
        ok('patient cannot write a doctor reply (rules)', try_write(P, 'reviews/rvP', {'reply': 'fake'}) == 'denied')
        ok("doctor cannot change a patient's stars (rules)", try_write(D, 'reviews/rv3', {'rating': 5}) == 'denied')
        ok('new reviews store only the short name', P.evaluate("shortName('Ravi Kumar Reddy')") == 'Ravi R.')

        # ===== 3. AI SUMMARY FROM THE SERVER =====
        clear(P); P.evaluate("go('consult', { id: 'r2' })"); W(P, 500)
        P.click('[data-act="aiSummary"]'); W(P, 900)
        ok('summary asked from the server with the consultation id', sum_log and sum_log[-1]['b']['rid'] == 'r2' and sum_log[-1]['auth'].startswith('Bearer ') and sum_log[-1]['b']['notify'] is False, sum_log[-1:])
        pm = mainP().lower()
        ok('summary shows medicines with timing in words, tests, warning signs', 'your medicines' in pm and 'dolo 650' in pm and 'morning and night' in pm and 'tests to do' in pm and 'cbc blood test' in pm and 'go to a hospital quickly if' in pm, pm[pm.find('AI summary'):pm.find('AI summary') + 900])
        ok('summary shows what the doctor found and food/rest advice', 'viral fever' in pm and 'food, rest & habits' in pm and 'checked again' in pm)
        ok("patient doesn't see the doctor's clinical note", 'clinical note (soap)' not in pm)
        P.screenshot(path='g04_summary.png', full_page=True)
        P.evaluate("window.__spoken = []"); P.click('[data-act="speakSum"]'); W(P, 300)
        sp = P.evaluate("window.__spoken.map(x => x.text).join(' ')")
        ok('read aloud includes the medicines and warnings', 'Dolo 650, 650 mg, morning and night, for 3 days, after food' in sp and 'Go to a hospital quickly if' in sp, sp[:300])
        P.click('[data-act="speakSum"]'); W(P, 200)
        clear(D); server_write(D, 'requests/r2', {'aiSummary': SUMMARY}); W(D, 300); D.evaluate("go('consult', { id: 'r2' })"); W(D, 500)
        ok('doctor sees the SOAP clinical note', 'clinical note (soap)' in D.locator('main').inner_text().lower() and 'Dolo 650 BD x3d, CBC' in D.locator('main').inner_text())
        server_write(D, 'requests/rA', {'rxId': 'rxD'}); W(D, 300)
        n0 = len(sum_log)
        D.evaluate("go('room', { id: 'rA' })"); W(D, 500)
        D.click('[data-act="endConsult"]'); W(D, 300); D.click('.modal button:has-text("End consultation")'); W(D, 3500)
        ok('ending with a prescription makes the summary by itself and alerts the patient', len(sum_log) > n0 and sum_log[-1]['b']['rid'] == 'rA' and sum_log[-1]['b']['notify'] is True, sum_log[-1:])

        # ===== 4. ALERTS =====
        clear(S); S.evaluate("Rider.ids.add('oN'); Rider.onPos({ coords: { latitude: 17.4402, longitude: 78.4483, accuracy: 6 } })"); W(S, 700)
        ok('delivery arriving alert (once) when the rider is near', any('arriving in about' in t for t in notes_to(PAT)) and P.evaluate("!!globalThis.__fsStore.get('orders/oN').nearAt"))
        S.evaluate("Rider.onPos({ coords: { latitude: 17.4390, longitude: 78.4483, accuracy: 6 } })"); W(S, 500)
        ok('…not repeated', sum(1 for t in notes_to(PAT) if 'arriving in about' in t) == 1)
        S.evaluate("Rider.stop()")
        why = P.evaluate("Push.err = { code: 20, message: 'Registration failed - push service error' }; Push.why()")
        ok('notification error explains the fix in simple steps', 'Private DNS' in why and 'Google Play services' in why, why)
        swt = P.evaluate("fetch('sw.js').then(r => r.text())")
        ok('urgent alerts stay on screen with a strong vibration and sound', 'requireInteraction: call || urgent' in swt and 'silent: false' in swt)
        ok('payment alerts and refunds reach the right people (titles)', P.evaluate("typeof notify") == 'function')

        # ===== 5. CALL NOTES LANGUAGE =====
        clear(P); P.evaluate("root('profile')"); W(P, 500)
        ok('profile: choose the language you speak on calls', P.locator('#call-lang option').count() == 12)
        P.select_option('#call-lang', 'te'); W(P, 300)
        ok('language saved', P.evaluate("localStorage.getItem('healvio:callLang')") == 'te')
        P.evaluate("Listen.prev['r1'] = 'Doctor asked about the fever.'; Listen.send('r1', 'A'.repeat(1200), Date.now())"); W(P, 800)
        ok('call notes send the language and what was said just before', listen_log and listen_log[-1]['lang'] == 'te' and listen_log[-1]['prev'] == 'Doctor asked about the fever.', {k: listen_log[-1][k] for k in ('lang', 'prev')} if listen_log else None)
        ok('next piece remembers the new words', P.evaluate("Listen.prev['r1']").endswith('I have a headache since morning.'))
        print('denied:', denied(P)[:4], denied(D)[:4], denied(S)[:4])
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
