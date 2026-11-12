import re, json, subprocess, time
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8092'))
SEED['prescriptions/rxE'] = {'id': 'rxE', 'requestId': 'r1', 'patientId': PAT, 'doctorId': DOC, 'createdAt': T - 5e7, 'diagnosis': 'Cough',
                            'medicines': [{'name': 'Ascoril syrup 10 ml 1-1-1 5 days, Levocetirizine 5 mg 0-0-1 5 days', 'dose': '', 'freq': '', 'days': '', 'note': ''}]}
def notes_of(p, who):
    return [v['text'] for k, v in p.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('notifications/') and v.get('to') == who]
def order_of(p, rx, mode):
    return [v for k, v in p.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('orders/') and v.get('rxId') == rx and v.get('mode') == mode]
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, geolocation=HOME, permissions=['geolocation'])
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
        ctx.route('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=FAKE_L))
        ctx.route('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', lambda r: r.fulfill(status=200, content_type='text/css', body=''))
        ctx.route(re.compile(r'https://nominatim\.openstreetmap\.org/reverse.*'), nominatim)
        ctx.route(re.compile(r'https://tile\.openstreetmap\.org/.*'), lambda r: r.abort())
        pages = {}
        for who in ['D', 'P', 'S']:
            p = ctx.new_page(); p.on('pageerror', lambda e, who=who: errs.append((who, str(e))))
            p.goto(URL); W(p, 1400); pages[who] = p
        D, P, S = pages['D'], pages['P'], pages['S']
        seed(D); W(D, 400)
        for p, email, name in [(D, DOC_E, 'Ananya Rao'), (P, PAT_E, 'Ravi Kumar'), (S, ST_E, 'Ramesh')]:
            p.evaluate(f"globalThis.__googleEmail={json.dumps(email)}; globalThis.__googleName={json.dumps(name)}")
            p.click('button:has-text("Continue with Google")'); W(p, 1200)
        clear = lambda p: (p.evaluate("state.confirm = null; state.modal = null; render()"), W(p, 150))
        for p in (P, D, S): clear(p)
        mainP = lambda: P.locator('main').inner_text()

        # ================= PICK UP =================
        P.evaluate("root('pStores')"); W(P, 600)
        ok('Medicines tab: one clear "Order medicines" button + how it works', P.locator('[data-act="newOrder"]:has-text("Order medicines")').count() == 1 and 'Pick up or delivery' in mainP() and 'Pay with PayPal' in mainP())
        ok('each partner store has "Order from here"', P.locator('[data-act="newOrder"][data-store]:has-text("Order from here")').count() >= 1)
        P.screenshot(path='o01_tab.png')
        P.click('[data-act="newOrder"]:has-text("Order medicines")'); W(P, 600)
        ok('order screen has 3 numbered steps', P.locator('.wz .n').count() == 3 and 'Choose the prescription' in mainP() and 'How do you want your medicines?' in mainP() and 'Choose the store' in mainP())
        ok('Send is locked until all 3 are chosen', P.locator('[data-act="placeOrder"]').is_disabled())
        ok('prescriptions list shows the medicine names', 'Ascoril syrup, Levocetirizine' in mainP() and 'Paracetamol, Cetirizine' in mainP())
        P.click('[data-act="ordPick"][data-k="rxId"][data-v="rxE"]'); W(P, 200)
        P.click('[data-act="ordPick"][data-k="mode"][data-v="pickup"]'); W(P, 200)
        ok('still locked without a store', P.locator('[data-act="placeOrder"]').is_disabled() and P.locator('.wz .n.done').count() == 2)
        P.click(f'[data-act="ordPick"][data-k="storeId"][data-v="{ST}"]'); W(P, 200)
        ok('"What happens next" says: price → PayPal or counter → collect', 'Store checks medicines' in mainP() and 'or at the counter' in mainP() and 'Collect at the store' in mainP())
        P.screenshot(path='o02_wizard.png')
        P.click('[data-act="placeOrder"]'); W(P, 900)
        o1 = order_of(P, 'rxE', 'pickup'); o1id = o1[0]['id'] if o1 else ''
        ok('pick-up order sent; opens the order page', o1 and P.evaluate("state.view") == 'order' and 'Waiting for Sri Ram Medicals' in mainP() and 'You pay only after that' in mainP(), mainP()[:300])
        ok('store alerted "New pick-up order"', any('New pick-up order' in t for t in notes_of(S, ST)))
        # duplicate guard
        P.evaluate("root('pStores')"); W(P, 300)
        P.evaluate(f"state.form.ord = {{ rxId: 'rxE', mode: 'pickup', storeId: '{ST}' }}; ACT.placeOrder()"); W(P, 600)
        ok('same prescription to the same store again → opens the existing order', len(order_of(P, 'rxE', 'pickup')) == 1 and P.evaluate("state.view") == 'order' and P.evaluate("state.params.id") == o1id)
        # store
        clear(S); S.evaluate("state.tab.so = 'new'; root('sOrders')"); W(S, 600)
        ok('store tabs: New / In progress / Done, with a one-line how-to', S.locator('.seg button').count() == 3 and 'tick ✓ the medicines you have' in S.locator('main').inner_text())
        card = S.locator(f'.card:has([data-act="ordRespond"][data-id="{o1id}"])')
        ok('store card says what to do now', 'New order · check the medicines' in card.inner_text() and 'Pick up at store' in card.inner_text())
        for i in range(2): S.locator(f'[data-act="ordItem"][data-id="{o1id}"][data-i="{i}"][data-v="1"]').click(); W(S, 200)
        S.fill(f'#op-{o1id}-0', '85'); S.fill(f'#op-{o1id}-1', '35')
        S.click(f'[data-act="ordRespond"][data-id="{o1id}"]'); W(S, 800)
        ok('price sent (₹120)', S.evaluate(f"globalThis.__fsStore.get('orders/{o1id}').total") == 120)
        ok('patient alert explains paying', any('Total ₹120. Pay in the app with PayPal, or at the counter.' in t for t in notes_of(P, PAT)))
        # patient pays from the list
        clear(P); P.evaluate("root('pStores')"); W(P, 500)
        mini = P.locator(f'.card:has([data-act="payOrder"][data-id="{o1id}"])')
        ok('list card: "confirmed · ₹120" with "Pay ₹120 with PayPal"', 'Sri Ram Medicals confirmed · ₹120' in mini.inner_text() and 'Pay ₹120 with PayPal' in mini.inner_text() and 'Pay now to book them, or pay at the counter' in mini.inner_text(), mini.inner_text())
        P.screenshot(path='o03_confirmed.png')
        INR[o1id] = 120
        P.click(f'[data-act="payOrder"][data-id="{o1id}"]'); W(P, 900)
        ok('tapping Pay opens PayPal (not the order page)', P.locator('#pp-ov').count() == 1 and P.evaluate("state.view") == 'pStores')
        P.click('#fake-pp'); W(P, 900)
        server_write(S, f'orders/{o1id}', {'paid': {'by': 'paypal', 'orderId': 'P1', 'captureId': 'C1', 'amount': '1.26', 'currency': 'USD', 'inr': 120, 'at': T + 100, 'test': True}}); W(P, 500)
        P.evaluate("render()"); W(P, 200)
        mini = P.locator(f'.card[data-id="{o1id}"]')
        ok('after paying: "Paid · ready to collect" + Directions', 'Paid · ready to collect' in mini.inner_text() and mini.locator('a:has-text("Directions")').count() == 1, mini.inner_text())
        # open details
        mini.click(); W(P, 500)
        ok('order page: steps, medicines, total, paid line', P.evaluate("state.view") == 'order' and P.locator('.steps > div.on').count() == 3 and 'Total' in mainP() and '₹120' in mainP() and 'Paid ₹120 with PayPal' in mainP(), mainP()[:500])
        P.screenshot(path='o04_order_page.png')
        # store hands over
        clear(S); S.evaluate("state.tab.so = 'active'; render()"); W(S, 400)
        sc = S.locator(f'.card:has([data-act="ordCollected"][data-id="{o1id}"])')
        ok('store "In progress": "Paid ₹120 with PayPal · keep ready" + Handed over', 'Paid ₹120 with PayPal' in sc.inner_text() and 'Handed over' in sc.inner_text())
        S.click(f'[data-act="ordCollected"][data-id="{o1id}"]'); W(S, 300); S.click('.modal button:has-text("Yes, handed over")'); W(S, 700)
        ok('collected', S.evaluate(f"globalThis.__fsStore.get('orders/{o1id}').status") == 'collected' and any('You collected your medicines' in t for t in notes_of(P, PAT)))
        P.evaluate("root('pStores')"); W(P, 400)
        ok('finished orders move to "past orders"', P.locator('[data-act="togglePast"]').count() == 1 and P.locator(f'.card[data-id="{o1id}"]').count() == 0)

        # ================= HOME DELIVERY =================
        P.click(f'[data-act="newOrder"][data-store="{ST}"]'); W(P, 600)
        ok('"Order from here" pre-selects the store', P.locator(f'.opt.on[data-k="storeId"][data-v="{ST}"]').count() == 1)
        P.click('[data-act="ordPick"][data-k="rxId"][data-v="rxD"]'); W(P, 200)
        P.click('[data-act="ordPick"][data-k="mode"][data-v="delivery"]'); W(P, 1800)
        ok('choosing delivery opens the map to set the address', P.locator('#loc-ov').count() == 1 and 'Ameerpet Main Road' in P.locator('#loc-addr').input_value())
        P.fill('#loc-addr', 'Flat 302, Sai Residency, Ameerpet, Hyderabad 500016'); P.click('#loc-ov [data-ok]'); W(P, 500)
        ok('address shown in step 2; "what next" mentions cash at the door', 'Flat 302, Sai Residency' in mainP() and 'or cash at the door' in mainP() and 'Delivered to your door' in mainP())
        P.screenshot(path='o05_wizard_delivery.png')
        P.click('[data-act="placeOrder"]'); W(P, 900)
        o2 = order_of(P, 'rxD', 'delivery'); o2id = o2[0]['id']
        ok('delivery order sent with the address', o2[0]['delivery']['lat'] == HOME['latitude'] and 'Waiting for Sri Ram Medicals' in mainP())
        clear(S); S.evaluate("state.tab.so = 'new'; render()"); W(S, 500)
        for i in range(2): S.locator(f'[data-act="ordItem"][data-id="{o2id}"][data-i="{i}"][data-v="1"]').click(); W(S, 200)
        S.fill(f'#op-{o2id}-0', '60'); S.fill(f'#op-{o2id}-1', '40'); S.fill(f'#of-{o2id}', '25')
        S.click(f'[data-act="ordRespond"][data-id="{o2id}"]'); W(S, 800)
        ok('total ₹125 with delivery fee', S.evaluate(f"globalThis.__fsStore.get('orders/{o2id}').total") == 125)
        P.evaluate("render()"); W(P, 300)
        ok('patient: "confirmed · ₹125 · pay now or cash at the door"', 'Sri Ram Medicals confirmed · ₹125' in mainP() and 'Pay now to get them delivered, or pay cash at the door' in mainP() and 'Delivery fee' in mainP())
        # cash on delivery: store starts without payment
        clear(S); S.evaluate("state.tab.so = 'active'; render()"); W(S, 400)
        sc = S.locator(f'.card:has([data-act="startDelivery"][data-id="{o2id}"])')
        ok('store: "Waiting for the patient to pay ₹125 … you can start and collect cash"', 'Waiting for the patient to pay ₹125' in sc.inner_text() and 'collect cash' in sc.inner_text() and 'WHO IS DELIVERING?' in sc.inner_text())
        ctx.set_geolocation(SHOP)
        S.fill(f'#rn-{o2id}', 'Suresh'); S.fill(f'#rp-{o2id}', '9876543210')
        S.click(f'[data-act="startDelivery"][data-id="{o2id}"]'); W(S, 2500)
        sc = S.locator(f'.card:has([data-act="markDelivered"][data-id="{o2id}"])')
        ok('store: "Out for delivery · Collect ₹125 in cash" + Map + Delivered', 'Out for delivery' in sc.inner_text() and 'Collect ₹125 in cash' in sc.inner_text() and sc.locator('[data-act="trackOrder"]').count() == 1)
        S.screenshot(path='o06_store_out.png')
        P.evaluate("render()"); W(P, 500)
        ok('patient: "On the way · about N min … pay ₹125 in cash" + Track live', 'On the way · about' in mainP() and 'Pay ₹125 in cash at the door' in mainP() and P.locator('[data-act="trackOrder"]:has-text("Track live")').count() == 1, mainP()[:300])
        ok('patient can call the delivery partner', P.locator('a[href="tel:9876543210"]').count() >= 1)
        P.screenshot(path='o07_patient_out.png')
        P.click('[data-act="trackOrder"]'); W(P, 2500)
        ok('live map: home + rider, ETA', P.locator('#trk-map .fake-marker').count() == 2 and 'min' in P.locator('#trk-info').inner_text())
        P.click('#trk-ov [data-x]'); W(P, 200)
        clear(S); S.click(f'[data-act="markDelivered"][data-id="{o2id}"]'); W(S, 300); S.click('.modal button:has-text("Delivered")'); W(S, 800)
        P.evaluate("render()"); W(P, 400)
        ok('patient: Delivered, all steps done', 'Delivered' in mainP() and P.locator('.steps > div.on').count() == 5)

        # ================= NOT AVAILABLE =================
        server_write(S, 'orders/oNA', {'id': 'oNA', 'rxId': 'rxE', 'storeId': ST, 'patientId': PAT, 'storeName': 'Sri Ram Medicals', 'mode': 'pickup', 'status': 'unavailable', 'items': [{'name': 'X', 'available': False}], 'createdAt': T, 'updatedAt': T + 9e6})
        W(P, 400); P.evaluate("state.filters.pastOrd = true; root('pStores')"); W(P, 400)
        na = P.locator('.card[data-id="oNA"]')
        ok('not available → "Try another store" opens the order screen with that prescription', 'Not available at Sri Ram Medicals' in na.inner_text())
        na.locator('[data-act="newOrder"]').click(); W(P, 500)
        ok('...prescription already chosen', P.evaluate("state.view") == 'orderNew' and P.locator('.opt.on[data-k="rxId"][data-v="rxE"]').count() == 1)
        # prescription page has one clear button
        P.evaluate("go('rxView', { id: 'rxD' })"); W(P, 500)
        ok('prescription page: "Order these medicines (pick up or delivery)"', P.locator('[data-act="newOrder"][data-rx="rxD"]').count() == 1)
        print('denied:', denied(P), denied(S))
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
