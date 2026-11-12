import re, json, subprocess, time
from playwright.sync_api import sync_playwright
V = '13.2.0'
errs, results = [], []
def ok(name, cond, extra=''):
    results.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (' | ' + str(extra)[:300] if extra != '' else ''))
srv = subprocess.Popen(['python3', '-m', 'http.server', '8088'], cwd='/home/claude/healvio-app', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
URL = 'http://localhost:8088/'
CFG = 'window.HEALVIO_CONFIG = { production: true, firebase: { apiKey: "x", authDomain: "h.firebaseapp.com", projectId: "healvio-test", messagingSenderId: "1", appId: "1:2:web:3" }, phoneLogin: false, server: "https://w.healvio.test/", vapidKey: "VAPID-KEY" };'
src = open('t9_calls.py').read()
exec(src[src.index("def W(p"):src.index("try:\n    with sync_playwright")].replace("8082", "8088"))
ST_E = 'srirammedicals@example.com'; ST = gid(ST_E)
store_info = {'name': 'Sri Ram Medicals', 'address': '12 MG Road', 'area': 'Ameerpet', 'city': 'Hyderabad', 'pincode': '500016', 'phone': '9000000003', 'hours': '8 AM - 10 PM', 'license': 'DL-123'}
SEED.update({
    f'accounts/{ST}': {'id': ST, 'role': 'store', 'name': 'Ramesh', 'email': ST_E, 'phone': '9000000003', 'status': 'approved', 'createdAt': T, 'store': store_info},
    f'public/{ST}': {'id': ST, 'role': 'store', 'name': 'Ramesh', 'status': 'approved', 'demo': False, 'store': store_info, 'phone': '9000000003'},
    'requests/rA': {'id': 'rA', 'patientId': PAT, 'doctorId': DOC, 'status': 'accepted', 'mode': 'video', 'type': 'normal', 'problem': 'Back pain for a week', 'createdAt': T, 'acceptedAt': T,
                    'patient': {'name': 'Ravi Kumar', 'age': 30, 'phone': '9000000002'}, 'prefDate': '2026-11-11', 'slotDate': '2026-11-11', 'slotTime': '11:00', 'acceptedFor': '11 Nov, 11:00 AM'},
    'prescriptions/rx1': {'id': 'rx1', 'requestId': 'r2', 'patientId': PAT, 'doctorId': DOC, 'createdAt': T - 8e7, 'diagnosis': 'Viral fever', 'medicines': [{'name': 'Paracetamol 650', 'dose': '1 tab', 'freq': 'Twice a day', 'days': '3'}, {'name': 'ORS sachet', 'dose': '1', 'freq': 'Once a day', 'days': '3'}]},
    'orders/o1': {'id': 'o1', 'rxId': 'rx1', 'storeId': ST, 'patientId': PAT, 'patient': {'name': 'Ravi Kumar', 'phone': '9000000002'}, 'doctorName': 'Dr. Ananya Rao', 'storeName': 'Sri Ram Medicals', 'status': 'sent',
                  'items': [{'name': 'Paracetamol 650', 'dose': '1 tab', 'freq': 'Twice a day', 'days': '3', 'available': None}, {'name': 'ORS sachet', 'dose': '1', 'freq': 'Once a day', 'days': '3', 'available': None}], 'createdAt': T, 'updatedAt': T},
})
H = {'Access-Control-Allow-Origin': 'http://localhost:8088', 'Access-Control-Allow-Headers': 'content-type, authorization', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'}
PAYPAL = {'clientId': 'SBX-CLIENT', 'env': 'sandbox', 'currency': 'USD', 'rate': 95}
status = {'ai': True, 'listen': True, 'push': True, 'turn': False, 'paypal': PAYPAL}
pay_log, sdk_urls = [], []
mode = {'capture': 'ok', 'sdk': 'ok'}
INR = {'rA': 300, 'o1': 250}
def j(route, obj, st=200):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    route.fulfill(status=st, headers={**H, 'content-type': 'application/json'}, body=json.dumps(obj))
def pay_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    b = json.loads(route.request.post_data); step = route.request.url.rstrip('/').rsplit('/', 1)[1]
    pay_log.append({'step': step, 'b': b, 'auth': route.request.headers.get('authorization')})
    if step == 'create': return j(route, {'orderID': 'PPO%d' % len(pay_log), 'value': '%.2f' % (INR[b['id']] / 95), 'currency': 'USD', 'inr': INR[b['id']]})
    if mode['capture'] == 'declined': mode['capture'] = 'ok'; return j(route, {'error': 'Your payment method was declined. Please choose another.', 'retry': True}, 402)
    if mode['capture'] == 'mismatch': mode['capture'] = 'ok'; return j(route, {'error': 'The amount paid does not match the price. Contact Healvio support.'}, 409)
    j(route, {'ok': True, 'paid': {'by': 'paypal', 'orderId': b['orderID'], 'captureId': 'CAP-' + b['orderID'], 'amount': '%.2f' % (INR[b['id']] / 95), 'currency': 'USD', 'inr': INR[b['id']], 'at': T + 1000, 'test': True}})
FAKE_SDK = r"""
window.paypal = { Buttons(opts) { return { render(sel) {
  const el = document.querySelector(sel), b = document.createElement('button');
  b.id = 'fake-pp'; b.textContent = 'PayPal'; b.style.cssText = 'display:block;width:100%;height:46px;border-radius:23px;background:#ffc439;color:#003087;font:700 17px sans-serif;border:0';
  b.onclick = async () => {
    let id; try { id = await opts.createOrder(); } catch (e) { opts.onError(e); return; }
    window.__ppOrder = id;
    if (window.__ppMode === 'cancel') { opts.onCancel({ orderID: id }); return; }
    await opts.onApprove({ orderID: id }, { restart: () => { window.__ppRestart = (window.__ppRestart || 0) + 1; } });
  };
  el.appendChild(b); return Promise.resolve();
} }; } };
"""
def sdk_route(route):
    sdk_urls.append(route.request.url)
    if mode['sdk'] == 'fail': return route.abort()
    route.fulfill(status=200, content_type='application/javascript', body=FAKE_SDK)
def server_write(p, path, patch):  # what the worker does after PayPal confirms
    p.evaluate("""([path, patch]) => { const bc = new BroadcastChannel('fs-sync'); const d = { ...(globalThis.__fsStore.get(path) || {}), ...patch };
      globalThis.__fsStore.set(path, d); bc.postMessage({ t: 'w', path, d }); globalThis.__fsFire(); }""", [path, patch])
def try_write(p, path, patch):
    return p.evaluate("""([path, patch]) => { const [c, id] = path.split('/'); return Store.db.collection(c).doc(id).update(patch).then(() => 'allowed', e => 'denied'); }""", [path, patch])
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
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
        ctx.route(re.compile(r'https://w\.healvio\.test/pay/(create|capture)$'), pay_route)
        ctx.route(re.compile(r'https://www\.paypal\.com/sdk/js.*'), sdk_route)
        pages = {}
        for who in ['D', 'P', 'S']:
            p = ctx.new_page()
            p.on('pageerror', lambda e, who=who: errs.append((who, str(e))))
            p.goto(URL); W(p, 1400); pages[who] = p
        D, P, S = pages['D'], pages['P'], pages['S']
        seed(D); W(D, 400)
        for p, email, name in [(D, DOC_E, 'Ananya Rao'), (P, PAT_E, 'Ravi Kumar'), (S, ST_E, 'Ramesh')]:
            p.evaluate(f"globalThis.__googleEmail={json.dumps(email)}; globalThis.__googleName={json.dumps(name)}")
            p.click('button:has-text("Continue with Google")'); W(p, 1200)
            for sel in ['.modal button:has-text("Later")', '.modal button:has-text("Cancel")']:
                if p.locator(sel).count(): p.click(sel); W(p, 200)
        ok('PayPal switched on by itself from the worker (no config change)', P.evaluate("Pay.ok() && CFG().payUrl === 'https://w.healvio.test/pay' && CFG().paypal.clientId === 'SBX-CLIENT' && CFG().paypal.sandbox === true"), P.evaluate("[CFG().payUrl, CFG().paypal]"))
        ok('PayPal script is not loaded until someone pays (app stays fast)', len(sdk_urls) == 0)

        # ---- consultation fee ----
        P.evaluate("root('pConsults')"); W(P, 500)
        ok('consults list nudges the patient to pay', 'Pay ₹300 fee with PayPal' in P.locator('main').inner_text())
        P.evaluate("go('consult', { id: 'rA' })"); W(P, 500)
        box = P.locator('.paybox').inner_text()
        ok('patient sees the fee box with the dollar amount', 'Consultation fee · ₹300' in box and 'US$3.16' in box and P.locator('.paybox [data-act="payFee"]').count() == 1, box)
        P.screenshot(path='pp01_patient_fee.png')
        D.evaluate("go('consult', { id: 'rA' })"); W(D, 500)
        ok('doctor sees "not paid yet" (no pay button)', 'not paid yet' in D.locator('.paybox').inner_text() and D.locator('[data-act="payFee"]').count() == 0, D.locator('.paybox').inner_text())

        for p in (P, D, S):
            p.evaluate("state.confirm = null; state.modal = null; render()"); W(p, 150)
        # SDK fails to load
        mode['sdk'] = 'fail'
        P.click('[data-act="payFee"]'); W(P, 900)
        ok("PayPal's card script can't load: the main Pay with PayPal button still works, card option hidden, nothing charged", P.locator('#pp-go').count() == 1 and P.locator('#pp-ov .pp-or').count() == 0 and not pay_log, P.locator('#pp-ov').inner_text())
        P.click('#pp-ov [data-pp="x"]'); W(P, 200)
        ok('close button closes the payment sheet', P.locator('#pp-ov').count() == 0)
        mode['sdk'] = 'ok'

        P.click('[data-act="payFee"]'); W(P, 900)
        ov = P.locator('#pp-ov').inner_text()
        ok('payment sheet: amount, who, test-mode tag, PayPal button', '₹300' in ov and 'Dr. Ananya Rao' in ov and 'Test mode' in ov and 'US$3.16' in ov and P.locator('#fake-pp').count() == 1, ov)
        u = sdk_urls[-1]
        ok('PayPal script asked with our client id, USD, capture', 'client-id=SBX-CLIENT' in u and 'currency=USD' in u and 'intent=capture' in u, u)
        P.screenshot(path='pp02_sheet.png')
        # the app re-draws while the sheet is open: the PayPal button must survive
        P.evaluate("render()"); W(P, 200)
        ok('PayPal button survives app redraws', P.locator('#fake-pp').count() == 1)

        # cancel
        P.evaluate("window.__ppMode = 'cancel'"); P.click('#fake-pp'); W(P, 600)
        ok('cancel: friendly message, nothing paid', 'cancelled' in P.locator('#pp-msg').inner_text() and not P.evaluate("Store.data.requests.rA.paid"), P.locator('#pp-msg').inner_text())
        # declined → restart
        P.evaluate("window.__ppMode = ''"); mode['capture'] = 'declined'; P.click('#fake-pp'); W(P, 800)
        ok('declined card: asks to choose another way (PayPal restart)', P.evaluate("window.__ppRestart") == 1 and 'declined' in P.locator('#pp-msg').inner_text(), P.locator('#pp-msg').inner_text())
        # success
        n0 = len(pay_log)
        P.click('#fake-pp'); W(P, 900)
        cr = [x for x in pay_log[n0:] if x['step'] == 'create']; cp = [x for x in pay_log[n0:] if x['step'] == 'capture']
        ok('app asks the worker to create and capture (signed in, no price sent)', cr and cp and cr[0]['b'] == {'kind': 'fee', 'id': 'rA'} and cp[0]['b']['orderID'] == cr and True or (cr and cp and cr[0]['b'] == {'kind': 'fee', 'id': 'rA'} and cp[0]['b']['orderID'].startswith('PPO') and (cp[0]['auth'] or '').startswith('Bearer idtoken-')), pay_log[n0:])
        print('DBG', P.evaluate("[document.querySelector('#pp-msg') && document.querySelector('#pp-msg').textContent, !!document.querySelector('#pp-ov'), JSON.stringify(Store.data.requests.rA.paid||null)]"), errs[-3:])
        ok('sheet closes and "Paid" toast shows', P.locator('#pp-ov').count() == 0 and 'Paid ₹300 with PayPal' in P.locator('body').inner_text())
        ok('patient sees "Fee paid" right away', 'Fee paid · ₹300' in P.locator('.paybox.ok').inner_text(), P.locator('main').inner_text()[:400])
        notes = P.evaluate("[...globalThis.__fsStore.entries()].filter(([k]) => k.startsWith('notifications/')).map(([k, v]) => [v.to, v.text])")
        ok('doctor and admin get an alert about the payment', any(t == DOC and 'paid your ₹300 consultation fee with PayPal' in x for t, x in notes) and any(t == 'admin' and 'PayPal payment' in x for t, x in notes), notes[-3:])
        P.screenshot(path='pp03_paid.png')
        # the worker writes "paid" to the database → doctor sees it
        server_write(D, 'requests/rA', {'paid': {'by': 'paypal', 'orderId': 'PPO9', 'captureId': 'CAP-PPO9', 'amount': '3.16', 'currency': 'USD', 'inr': 300, 'at': T + 1000, 'test': True}, 'updatedAt': T + 1000})
        W(D, 600); D.evaluate("render()"); W(D, 200)
        ok('doctor sees "Fee paid with PayPal"', 'Fee paid · ₹300' in D.locator('.paybox.ok').inner_text() and 'Fee paid with PayPal' in D.locator('.timeline').inner_text(), D.locator('main').inner_text()[:500])
        D.screenshot(path='pp04_doctor_paid.png')
        P.evaluate("render()"); W(P, 200)
        ok('patient can no longer pay twice', P.locator('[data-act="payFee"]').count() == 0)
        # security: nobody can fake "paid" from a phone
        ok('patient cannot mark a consultation paid', try_write(P, 'requests/r1', {'paid': {'by': 'paypal'}}) == 'denied')
        ok('doctor cannot mark a consultation paid', try_write(D, 'requests/r1', {'paid': {'by': 'paypal'}}) == 'denied')
        ok("patient cannot erase the doctor's paid record", try_write(P, 'requests/rA', {'paid': None}) == 'denied')
        r = P.evaluate("""Store.db.collection('requests').doc('rX').set({ id: 'rX', patientId: Store.authUser.uid, doctorId: '%s', status: 'requested', paid: { by: 'paypal' } }).then(() => 'allowed', e => 'denied')""" % DOC)
        ok('patient cannot create a request that is already "paid"', r == 'denied')

        # ---- medicine order ----
        S.evaluate("root('sOrders')"); W(S, 500)
        ok('store sees the new prescription with a price box', S.locator('[id="ot-o1"]').count() == 1)
        for i in range(2): S.locator(f'[data-act="ordItem"][data-i="{i}"][data-v="1"]').click(); W(S, 250)
        S.fill('#ot-o1', '250'); W(S, 100)
        S.fill('#on-o1', 'Ready after 5 PM'); W(S, 100)
        S.screenshot(path='pp05_store_price.png')
        S.click('[data-act="ordRespond"][data-id="o1"]'); W(S, 700)
        o = S.evaluate("globalThis.__fsStore.get('orders/o1')")
        ok('store sends availability with total ₹250', o['status'] == 'ready' and o['total'] == 250, {k: o.get(k) for k in ('status', 'total', 'note')})
        notes = S.evaluate("[...globalThis.__fsStore.entries()].filter(([k]) => k.startsWith('notifications/')).map(([k, v]) => [v.to, v.text])")
        ok('patient is told the total and that they can pay with PayPal', any(t == PAT and 'Total ₹250' in x and 'PayPal' in x for t, x in notes), notes[-2:])
        P.evaluate("root('pStores')"); W(P, 600)
        box = P.locator('.ohero.pay').inner_text()
        ok('patient sees "confirmed · ₹250" with Pay', 'confirmed · ₹250' in box and 'Pay ₹250 with PayPal' in box and P.locator('[data-act="payOrder"]').count() == 1, box)
        P.screenshot(path='pp06_patient_order.png')
        mode['capture'] = 'mismatch'
        P.click('[data-act="payOrder"]'); W(P, 900); P.click('#fake-pp'); W(P, 900)
        ok('price mismatch from the worker: shown, not marked paid', 'does not match' in P.locator('#pp-msg').inner_text() and not P.evaluate("Store.data.orders.o1.paid"))
        P.click('#fake-pp'); W(P, 900)
        ok('medicines paid', P.locator('#pp-ov').count() == 0 and 'Paid · ready to collect' in P.locator('main').inner_text(), P.locator('main').inner_text()[:500])
        server_write(S, 'orders/o1', {'paid': {'by': 'paypal', 'orderId': 'PPO20', 'captureId': 'CAP-PPO20', 'amount': '2.63', 'currency': 'USD', 'inr': 250, 'at': T + 2000, 'test': True}})
        W(S, 600); S.evaluate("state.confirm = null; state.tab.so = 'active'; render()"); W(S, 300)
        ok('store sees "Paid ₹250 with PayPal" and can hand over', 'Paid ₹250 with PayPal' in S.locator('main').inner_text() and S.locator('[data-act="ordCollected"]').count() == 1)
        S.screenshot(path='pp07_store_paid.png')
        ok('store alerted about the payment', any('paid ₹250 for their medicines with PayPal' in v.get('text', '') for k, v in S.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('notifications/') and v.get('to') == ST))
        ok('store cannot change the price after payment', try_write(S, 'orders/o1', {'total': 1}) == 'denied')
        ok('store cannot mark an order paid', try_write(S, 'orders/o1', {'paid': {'by': 'cash'}}) == 'denied')
        ok('patient cannot change the order price', try_write(P, 'orders/o1', {'total': 1}) == 'denied')

        # store adds the price later (order answered before this update)
        server_write(S, 'orders/o2', {'id': 'o2', 'rxId': 'rx1', 'storeId': ST, 'patientId': PAT, 'storeName': 'Sri Ram Medicals', 'status': 'partial', 'items': [{'name': 'ORS sachet', 'available': True}, {'name': 'X', 'available': False}], 'createdAt': T, 'updatedAt': T + 5000})
        W(S, 500); S.evaluate("render()"); W(S, 200)
        ok('store can add a price to an older order', S.locator('[data-act="ordPrice"][data-id="o2"]').count() == 1)
        S.fill('#ot-o2', '45.5'); S.click('[data-act="ordPrice"][data-id="o2"]'); W(S, 600)
        ok('price saved', S.evaluate("globalThis.__fsStore.get('orders/o2').total") == 45.5)

        # PayPal off on the worker → no pay buttons anywhere, app still works
        P.evaluate("CFG().paypal = null; CFG().payUrl = ''; render()"); W(P, 200)
        ok('when PayPal is off, no pay buttons show', P.locator('[data-act="payOrder"]').count() == 0 and P.locator('.paybox:not(.ok)').count() == 0 and P.locator('.ohero.pay .pp').count() == 0)
        print('denied (expected 6):', len(denied(P)) + len(denied(D)) + len(denied(S)))
        b.close()
finally:
    srv.terminate()
print('page errors:', errs[:5])
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
