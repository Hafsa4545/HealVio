import re, json, subprocess, time
from playwright.sync_api import sync_playwright
srcp = open('t16_paypal.py').read()
exec(srcp[:srcp.index("try:\n    with sync_playwright")].replace('8088', '8091'))
SEED[f'accounts/{DOC}']['doc']['system'] = 'Allopathy'
SEED[f'public/{DOC}']['doc'] = {**SEED[f'public/{DOC}']['doc'], 'system': 'Allopathy'}
SEED['prescriptions/rxD'] = {'id': 'rxD', 'requestId': 'r2', 'patientId': PAT, 'doctorId': DOC, 'createdAt': T - 6e7, 'diagnosis': 'Fever',
                            'medicines': [{'name': 'Paracetamol 650 mg 1-0-1 5 days, Cetirizine 10 mg 0-0-1 3 days', 'dose': '', 'freq': '', 'days': '', 'note': ''}]}
HOME = {'latitude': 17.4375, 'longitude': 78.4483}
SHOP = {'latitude': 17.4500, 'longitude': 78.4000}
NEAR = {'latitude': 17.4400, 'longitude': 78.4460}
FAKE_L = r"""
window.L = (() => {
  const LL = a => Array.isArray(a) ? { lat: a[0], lng: a[1] } : { lat: a.lat, lng: a.lng };
  function map(el) { el.classList.add('fake-map'); const m = { el, zoom: 0, h: {}, setView(c, z) { this.view = LL(c); this.zoom = z; el.dataset.view = JSON.stringify(this.view); return this; },
    getZoom() { return this.zoom; }, invalidateSize() {}, fitBounds(b) { el.dataset.fit = JSON.stringify(b); this.zoom = 15; return this; }, on(e, f) { this.h[e] = f; return this; }, remove() { el.innerHTML = ''; } };
    (window.__maps = window.__maps || []).push(m); return m; }
  function marker(c, o) { const m = { ll: LL(c), h: {}, addTo(mp) { this.el = document.createElement('div'); this.el.className = 'fake-marker'; this.el.innerHTML = (o && o.icon && o.icon.html) || ''; this.el.dataset.ll = JSON.stringify(this.ll); mp.el.appendChild(this.el); return this; },
    setLatLng(c) { this.ll = LL(c); if (this.el) this.el.dataset.ll = JSON.stringify(this.ll); return this; }, getLatLng() { return this.ll; }, on(e, f) { this.h[e] = f; return this; } };
    (window.__markers = window.__markers || []).push(m); return m; }
  return { map, marker, tileLayer: () => ({ addTo() { return this; } }), divIcon: o => o, latLngBounds: a => a };
})();
"""
geo_calls = []
def nominatim(route):
    geo_calls.append(route.request.url)
    route.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin': '*'},
                  body=json.dumps({'display_name': 'x', 'address': {'house_number': '12-4', 'road': 'Ameerpet Main Road', 'suburb': 'Ameerpet', 'city': 'Hyderabad', 'postcode': '500016'}}))
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

        # ---- patient: choose home delivery and set the location ----
        P.evaluate("go('rxView', { id: 'rxD' })"); W(P, 600); clear(P)
        P.click('[data-act="newOrder"][data-rx="rxD"]'); W(P, 500)
        ok('order screen offers pick up or home delivery', P.locator('[data-act="ordPick"][data-k="mode"][data-v="pickup"]').count() == 1 and P.locator('[data-act="ordPick"][data-k="mode"][data-v="delivery"]').count() == 1)
        ok('the prescription is already chosen', P.locator('.opt.on[data-k="rxId"][data-v="rxD"]').count() == 1)
        P.click('[data-act="ordPick"][data-k="mode"][data-v="delivery"]'); W(P, 1800)
        print('DBG', P.locator('#loc-ov').count(), P.locator('#loc-map').get_attribute('class') if P.locator('#loc-map').count() else None, P.locator('#loc-ov').inner_text()[:300] if P.locator('#loc-ov').count() else '', errs[-3:], P.evaluate("typeof window.L"))
        ok('choosing delivery opens the location picker with a map', P.locator('#loc-ov').count() == 1 and P.locator('#loc-map.fake-map').count() == 1)
        ok('it finds the patient by GPS and puts the pin there', P.evaluate("JSON.parse(document.querySelector('#loc-map .fake-marker').dataset.ll).lat") == HOME['latitude'], P.locator('#loc-msg').inner_text())
        ok('address is filled from the map location', 'Ameerpet Main Road' in P.locator('#loc-addr').input_value() and geo_calls, P.locator('#loc-addr').input_value())
        ok('phone is filled from the profile', P.locator('#loc-phone').input_value() == '9000000002')
        P.screenshot(path='d01_location.png')
        # drag the pin a little
        P.evaluate("(() => { const m = window.__markers[window.__markers.length - 1]; m.setLatLng([17.4380, 78.4490]); m.h.dragend(); })()"); W(P, 500)
        P.fill('#loc-land', 'Near Ram temple')
        P.fill('#loc-addr', 'Flat 302, Sai Residency, Ameerpet Main Road, Hyderabad 500016')
        P.click('#loc-ov [data-ok]'); W(P, 500)
        ok('confirmed: order screen shows "Deliver to" with the pin', P.locator('#loc-ov').count() == 0 and 'Flat 302, Sai Residency' in P.locator('main').inner_text() and 'pin on map' in P.locator('main').inner_text())
        P.screenshot(path='d02_sheet.png')
        P.click(f'[data-act="ordPick"][data-k="storeId"][data-v="{ST}"]'); W(P, 200)
        P.click('[data-act="placeOrder"]'); W(P, 900)
        o = [v for k, v in P.evaluate("Object.fromEntries(globalThis.__fsStore)").items() if k.startswith('orders/') and v.get('rxId') == 'rxD'][0]
        oid = o['id']
        ok('order saved as home delivery with address, phone and map point', o['mode'] == 'delivery' and o['delivery']['lat'] == 17.438 and o['delivery']['lng'] == 78.449 and o['delivery']['landmark'] == 'Near Ram temple' and o['delivery']['phone'] == '9000000002', o.get('delivery'))
        ok('each medicine is its own line', [i['name'] for i in o['items']] == ['Paracetamol', 'Cetirizine'])
        notes = P.evaluate("[...globalThis.__fsStore.entries()].filter(([k]) => k.startsWith('notifications/')).map(([k, v]) => [v.to, v.text])")
        ok('store alerted about a home delivery order', any(t == ST and 'New home delivery order' in x for t, x in notes), notes[-2:])
        r = P.evaluate("""Store.db.collection('orders').doc('ox').set({ id: 'ox', rxId: 'rxD', storeId: '%s', patientId: Store.authUser.uid, status: 'sent', mode: 'delivery', deliveryFee: 0, items: [] }).then(() => 'allowed', e => 'denied')""" % ST)
        ok('patient cannot set their own delivery fee', r == 'denied')

        # ---- store: confirm with prices and delivery fee ----
        clear(S); S.evaluate("root('sOrders')"); W(S, 700)
        card = S.locator(f'.card:has([data-act="ordRespond"][data-id="{oid}"])')
        ok('store sees "Home delivery", the address and Google Maps directions', 'Home delivery' in card.inner_text() and 'Flat 302' in card.inner_text() and card.locator('a[href*="google.com/maps/dir/"][href*="17.438,78.449"]').count() == 1)
        for i in range(2): S.locator(f'[data-act="ordItem"][data-id="{oid}"][data-i="{i}"][data-v="1"]').click(); W(S, 250)
        S.fill(f'#op-{oid}-0', '60'); S.fill(f'#op-{oid}-1', '40'); S.fill(f'#of-{oid}', '30')
        S.screenshot(path='d03_store_confirm.png')
        S.click(f'[data-act="ordRespond"][data-id="{oid}"]'); W(S, 800)
        o = S.evaluate(f"globalThis.__fsStore.get('orders/{oid}')")
        ok('total = medicines ₹100 + delivery ₹30', o['total'] == 130 and o['deliveryFee'] == 30 and o['status'] == 'ready', {k: o.get(k) for k in ('total', 'deliveryFee', 'status')})
        # ---- patient pays ----
        clear(P); P.evaluate("root('pStores')"); W(P, 700)
        P.evaluate(f"go('order', {{ id: '{oid}' }})"); W(P, 500)
        pc = P.locator('main .card').first
        ok('patient sees confirmed, delivery fee and Pay ₹130', 'confirmed · ₹130' in pc.inner_text() and 'Delivery fee' in pc.inner_text() and 'Pay ₹130 with PayPal' in pc.inner_text(), pc.inner_text()[:400])
        ok('progress steps: Sent ✓ Confirmed ✓', pc.locator('.steps > div.on').count() == 2)
        INR[oid] = 130
        P.click(f'[data-act="payOrder"][data-id="{oid}"]'); W(P, 900); P.click('#fake-pp'); W(P, 900)
        server_write(S, f'orders/{oid}', {'paid': {'by': 'paypal', 'orderId': 'PPX', 'captureId': 'CAP', 'amount': '1.37', 'currency': 'USD', 'inr': 130, 'at': T + 3000, 'test': True}}); W(S, 500)
        P.evaluate("render()"); W(P, 300)
        ok('paid with PayPal', 'Paid ₹130 with PayPal' in P.locator('main').inner_text())
        ok('store cannot change the delivery fee after payment', try_write(S, f'orders/{oid}', {'deliveryFee': 0}) == 'denied')

        # ---- store starts the delivery from the shop ----
        ctx.set_geolocation(SHOP); W(S, 200)
        clear(S); S.evaluate("state.tab.so = 'active'; render()"); W(S, 300)
        S.fill(f'#rn-{oid}', 'Suresh'); S.fill(f'#rp-{oid}', '9876543210')
        S.click(f'[data-act="startDelivery"][data-id="{oid}"]'); W(S, 2500)
        o = S.evaluate(f"globalThis.__fsStore.get('orders/{oid}')")
        ok('delivery started: out, rider name/phone saved', o['status'] == 'out' and o['riderName'] == 'Suresh' and o['riderPhone'] == '9876543210', {k: o.get(k) for k in ('status', 'riderName')})
        ok('store phone shares live location', o.get('rider') and abs(o['rider']['lat'] - SHOP['latitude']) < 1e-4 and S.evaluate(f"Rider.ids.has('{oid}')"), o.get('rider'))
        ok('store sees "Sharing live location" and Delivered', 'Sharing live location' in S.locator('main').inner_text() and S.locator(f'[data-act="markDelivered"][data-id="{oid}"]').count() == 1)
        notes = P.evaluate("[...globalThis.__fsStore.entries()].filter(([k]) => k.startsWith('notifications/')).map(([k, v]) => [v.to, v.text])")
        ok('patient told "on the way"', any(t == PAT and 'on the way with Suresh' in x for t, x in notes))
        S.screenshot(path='d04_store_out.png')
        # ---- patient tracks live ----
        P.evaluate("render()"); W(P, 500)
        km1 = P.evaluate(f"Geo.km(Store.data.orders['{oid}'].rider, Store.data.orders['{oid}'].delivery)")
        ok('patient order page shows "On the way · about N min"', 'On the way · about' in P.locator('main').inner_text() and 'Suresh' in P.locator('main').inner_text(), round(km1, 2))
        P.click(f'[data-act="trackOrder"][data-id="{oid}"]'); W(P, 2500)
        ok('tracking map shows home 🏠 and rider 🛵', P.locator('#trk-map .fake-marker').count() == 2 and '🛵' in P.locator('#trk-map').inner_html() and '🏠' in P.locator('#trk-map').inner_html())
        info1 = P.locator('#trk-info').inner_text()
        ok('ETA and distance shown, call button for the rider', 'min' in info1 and 'away' in info1 and P.locator('#trk-info a[href="tel:9876543210"]').count() == 1, info1)
        P.screenshot(path='d05_track.png')
        # rider moves closer
        ctx.set_geolocation(NEAR); W(S, 3000); W(P, 2500)
        o = S.evaluate(f"globalThis.__fsStore.get('orders/{oid}')")
        km2 = P.evaluate(f"Geo.km(Store.data.orders['{oid}'].rider, Store.data.orders['{oid}'].delivery)")
        ok('as the rider moves, the map and ETA update', abs(o['rider']['lat'] - NEAR['latitude']) < 1e-4 and km2 < km1 and P.evaluate(f"JSON.parse([...document.querySelectorAll('#trk-map .fake-marker')].find(e => e.innerHTML.includes('🛵')).dataset.ll).lat") == NEAR['latitude'], [round(km1, 2), round(km2, 2), P.locator('#trk-info').inner_text()])
        ok('patient cannot move the rider', try_write(P, f'orders/{oid}', {'rider': {'lat': 1, 'lng': 1, 'at': 1}}) == 'denied')
        # refresh on the store phone → sharing resumes by itself
        S.reload(); W(S, 2000)
        S.evaluate(f"globalThis.__googleEmail={json.dumps(ST_E)}; globalThis.__googleName='Ramesh'")
        if S.locator('button:has-text("Continue with Google")').count(): S.click('button:has-text("Continue with Google")'); W(S, 1500)
        clear(S); S.evaluate("root('sOrders')"); W(S, 1500)
        ok('after a refresh the store phone keeps sharing', S.evaluate(f"Rider.ids.has('{oid}')"))
        # delivered
        S.evaluate("state.tab.so = 'active'; render()"); W(S, 300)
        S.click(f'[data-act="markDelivered"][data-id="{oid}"]'); W(S, 300); S.click('.modal button:has-text("Delivered")'); W(S, 900)
        o = S.evaluate(f"globalThis.__fsStore.get('orders/{oid}')")
        ok('marked delivered, sharing stopped', o['status'] == 'delivered' and o.get('deliveredAt') and not S.evaluate("Rider.ids.size"), o['status'])
        W(P, 2500)
        ok('patient map says Delivered', 'Delivered' in P.locator('#trk-info').inner_text())
        P.click('#trk-ov [data-x]'); W(P, 300); P.evaluate("render()"); W(P, 300)
        pc = P.locator('main .card').first
        ok('patient order page: all 5 steps done', pc.locator('.steps > div.on').count() == 5, pc.inner_text()[:300])
        P.screenshot(path='d06_delivered.png')
        notes = P.evaluate("[...globalThis.__fsStore.entries()].filter(([k]) => k.startsWith('notifications/')).map(([k, v]) => [v.to, v.text])")
        ok('patient told "delivered"', any(t == PAT and 'were delivered' in x for t, x in notes))
        print('denied:', denied(P), denied(S))
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
