import re, json, subprocess, time
from playwright.sync_api import sync_playwright
srcp = open('t16_paypal.py').read()
exec(srcp[:srcp.index("try:\n    with sync_playwright")].replace('8088', '8090'))
SEED[f'accounts/{DOC}']['doc']['system'] = 'Allopathy'
SEED[f'public/{DOC}']['doc'] = {**SEED[f'public/{DOC}']['doc'], 'system': 'Allopathy'}
# an old prescription where the doctor typed everything with commas in one box
SEED['prescriptions/rxOld'] = {'id': 'rxOld', 'requestId': 'r2', 'patientId': PAT, 'doctorId': DOC, 'createdAt': T - 7e7, 'diagnosis': 'Cold',
                              'medicines': [{'name': 'Cetirizine 10 mg 0-0-1 3 days, Steam inhalation, Vicks', 'dose': '', 'freq': '', 'days': '', 'note': ''}]}
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
            p = ctx.new_page(); p.on('pageerror', lambda e, who=who: errs.append((who, str(e))))
            p.goto(URL); W(p, 1400); pages[who] = p
        D, P, S = pages['D'], pages['P'], pages['S']
        seed(D); W(D, 400)
        for p, email, name in [(D, DOC_E, 'Ananya Rao'), (P, PAT_E, 'Ravi Kumar'), (S, ST_E, 'Ramesh')]:
            p.evaluate(f"globalThis.__googleEmail={json.dumps(email)}; globalThis.__googleName={json.dumps(name)}")
            p.click('button:has-text("Continue with Google")'); W(p, 1200)
        for p in (P, D, S): p.evaluate("state.confirm = null; state.modal = null; render()"); W(p, 150)

        # --- doctor: quick add with commas ---
        D.evaluate("go('rxEdit', { id: 'r1' })"); W(D, 600)
        ok('prescription has a quick-add box for comma lists', D.locator('#rx-quick').count() == 1)
        D.fill('#rx-dx', 'Viral fever')
        D.fill('#rx-quick', 'Paracetamol 650 mg 1-0-1 5 days after food, Cetirizine 10 mg 0-0-1 3 days, ORS sachet')
        D.click('[data-act="rxQuick"]'); W(D, 400)
        rows = D.evaluate("state.form.rx.medicines.map(m => [m.name, m.dose, m.freq, m.days, m.note])")
        ok('"Add all" makes 3 separate medicines with dose, timing, days', rows == [['Paracetamol', '650 mg', '1-0-1', '5', 'after food'], ['Cetirizine', '10 mg', '0-0-1', '3', ''], ['ORS sachet', '', '', '', '']], rows)
        ok('the empty first row is replaced, quick box cleared', D.locator('.medrow input[id$="n"]').count() == 3 and D.locator('#rx-quick').input_value() == '')
        D.screenshot(path='m01_quick_add.png')
        # also: commas typed straight into one medicine box
        D.fill('#rx-m2n', 'ORS sachet, Vitamin C 500 mg 1-0-0 10 days')
        D.fill('#rx-quick', 'Steam inhalation twice a day')
        D.click('[data-act="saveRx"]'); W(D, 900)
        rx = [v for k, v in D.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('prescriptions/') and v.get('requestId') == 'r1']
        meds = rx[0]['medicines'] if rx else []
        ok('saved prescription splits commas everywhere (5 medicines)', [m['name'] for m in meds] == ['Paracetamol', 'Cetirizine', 'ORS sachet', 'Vitamin C', 'Steam inhalation'], meds)
        ok('Vitamin C got its own dose/timing/days', any(m['name'] == 'Vitamin C' and m['dose'] == '500 mg' and m['freq'] == '1-0-0' and m['days'] == '10' for m in meds))
        ok('text left in quick box is not lost on save', any(m['name'] == 'Steam inhalation' and m['freq'] == 'twice a day' for m in meds))
        rxid = rx[0]['id']

        # --- old prescription written in one box is shown as separate rows ---
        P.evaluate("go('rxView', { id: 'rxOld' })"); W(P, 600)
        names = P.evaluate("[...document.querySelectorAll('.rx tbody tr td:first-child b')].map(x => x.textContent)")
        ok('old comma prescription shows as 3 rows', names == ['Cetirizine', 'Steam inhalation', 'Vicks'], names)
        # --- patient sends the new prescription to the store ---
        P.evaluate(f"go('rxView', {{ id: '{rxid}' }})"); W(P, 600)
        P.screenshot(path='m02_rx_view.png')
        P.click('[data-act="newOrder"][data-rx]'); W(P, 500)
        P.click('[data-act="ordPick"][data-k="mode"][data-v="pickup"]'); W(P, 200)
        P.click(f'[data-act="ordPick"][data-k="storeId"][data-v="{ST}"]'); W(P, 200)
        P.click('[data-act="placeOrder"]'); W(P, 900)
        o = [v for k, v in P.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('orders/') and v.get('rxId') == rxid][0]
        ok('store order has each medicine as its own line', [i['name'] for i in o['items']] == ['Paracetamol', 'Cetirizine', 'ORS sachet', 'Vitamin C', 'Steam inhalation'], o['items'])
        oid = o['id']
        old = P.evaluate("(() => { const rx = Store.data.prescriptions.rxOld; return medsOf(rx).length; })()")
        ok('old prescriptions sent to a store also split (3 items)', old == 3)

        # --- store: mark, price each medicine, total adds itself ---
        S.evaluate("state.confirm = null; state.modal = null; root('sOrders')"); W(S, 600)
        av = [1, 1, 1, 1, 0]
        for i, v in enumerate(av): S.locator(f'[data-act="ordItem"][data-id="{oid}"][data-i="{i}"][data-v="{v}"]').click(); W(S, 250)
        ok('price box appears next to each available medicine', S.locator(f'[id^="op-{oid}-"]').count() == 4)
        for i, pr in enumerate(['40', '55.5', '20', '64.5']): S.fill(f'#op-{oid}-{i}', pr); W(S, 80)
        S.screenshot(path='m03_store_prices.png')
        S.click(f'[data-act="ordRespond"][data-id="{oid}"]'); W(S, 800)
        o = S.evaluate(f"globalThis.__fsStore.get('orders/{oid}')")
        ok('total = sum of medicine prices (₹180)', o['total'] == 180 and o['status'] == 'partial', {k: o.get(k) for k in ('total', 'status')})
        ok('each available medicine keeps its price', [i.get('price') for i in o['items']] == [40, 55.5, 20, 64.5, None], [i.get('price') for i in o['items']])
        # --- patient pays from the prescription page ---
        P.evaluate(f"state.confirm = null; state.modal = null; go('rxView', {{ id: '{rxid}' }})"); W(P, 700)
        box = P.locator('.ohero.pay').inner_text() if P.locator('.ohero.pay').count() else ''
        ok('prescription page shows the store reply and Pay', 'confirmed · ₹180' in box and P.locator('[data-act="payOrder"]').count() == 1, box)
        P.click(f'.card[data-id="{oid}"]'); W(P, 500)
        ok('order page lists each medicine with its price', '₹55.50' in P.locator('main').inner_text() and 'Steam inhalation' in P.locator('main').inner_text())
        P.screenshot(path='m04_rx_pay.png')
        INR[oid] = 180
        P.click('[data-act="payOrder"]'); W(P, 900); P.click('#fake-pp'); W(P, 900)
        ok('medicines paid with PayPal from the order page', 'Paid ₹180 with PayPal' in P.locator('main').inner_text(), P.locator('main').inner_text()[-400:])
        cr = [x for x in pay_log if x['step'] == 'create'][-1]
        ok('worker asked for this order (no price sent from the phone)', cr['b'] == {'kind': 'order', 'id': oid}, cr)
        # typed total still wins
        server_write(S, 'orders/o1', {'status': 'sent'}); W(S, 400); S.evaluate("state.tab.so = 'new'; render()"); W(S, 300)
        for i in range(2): S.locator(f'[data-act="ordItem"][data-id="o1"][data-i="{i}"][data-v="1"]').click(); W(S, 200)
        S.fill('#op-o1-0', '30'); S.fill('#ot-o1', '99'); S.click('[data-act="ordRespond"][data-id="o1"]'); W(S, 700)
        ok('a typed total is used as is', S.evaluate("globalThis.__fsStore.get('orders/o1').total") == 99)
        print('denied:', denied(P), denied(D), denied(S))
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
