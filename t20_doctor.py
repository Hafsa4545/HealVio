import re, json, subprocess, time, base64, io
from PIL import Image
from playwright.sync_api import sync_playwright
srcp = open('t16_paypal.py').read()
exec(srcp[:srcp.index("try:\n    with sync_playwright")].replace('8088', '8093'))
buf = io.BytesIO(); Image.open('../face.png').convert('RGB').save(buf, 'JPEG', quality=80)
PHOTO = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
info = {**SEED[f'public/{DOC}']['doc'], 'photo': PHOTO, 'system': 'Allopathy', 'specialization': 'General Physician', 'degree': 'MBBS, MD (General Medicine)', 'experience': 12,
        'hospital': 'Sri Sai Hospital', 'hospitalAddress': '12-4, MG Road, Ameerpet', 'city': 'Hyderabad', 'fee': 300, 'languages': 'English, Telugu, Hindi',
        'regNo': 'TSMC-45678', 'about': 'General physician with 12 years of experience in fever, diabetes and blood pressure care.', 'days': [1, 2, 3, 4, 5, 6], 'start': '00:00', 'end': '23:59', 'slot': 15}
SEED[f'public/{DOC}']['doc'] = info
SEED[f'accounts/{DOC}']['doc'] = {**SEED[f'accounts/{DOC}']['doc'], **info}
SEED['reviews/r2'] = {'id': 'r2', 'patientId': PAT, 'doctorId': DOC, 'rating': 5, 'review': 'Very clear and kind.', 'ratedAt': T - 3e6, 'patientName': 'Ravi K'}
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
        maps = []
        ctx.route(re.compile(r'https://maps\.google\.com/maps.*'), lambda r: (maps.append(r.request.url), r.fulfill(status=200, content_type='text/html', body='<body style="margin:0;background:#cfe3d9;font:14px sans-serif;display:flex;align-items:center;justify-content:center;height:100vh">Google map</body>')))
        P = ctx.new_page(); P.on('pageerror', lambda e: errs.append(str(e)))
        P.goto(URL); W(P, 1400); seed(P); W(P, 400)
        P.evaluate(f"globalThis.__googleEmail={json.dumps(PAT_E)}; globalThis.__googleName='Ravi Kumar'")
        P.click('button:has-text("Continue with Google")'); W(P, 1500)
        W(P, 2500); P.evaluate("state.confirm = null; state.modal = null; root('pHome')"); W(P, 500)
        # list: tap photo → zoom, tap card → profile
        P.locator(f'[data-act="zoomDoc"][data-id="{DOC}"]').first.click(); W(P, 400)
        ok('doctor list: tapping the photo opens it full screen', P.locator('#zoom-ov img').count() == 1 and P.evaluate("state.view") == 'pHome')
        P.click('#zoom-ov .zx'); W(P, 300)
        ok('close button closes the photo', P.locator('#zoom-ov').count() == 0)
        P.evaluate(f"go('pDoctor', {{ id: '{DOC}' }})"); W(P, 900)
        t = P.locator('main').inner_text()
        P.screenshot(path='dr01_profile_top.png')
        for lab, val in [('QUALIFICATION', 'MBBS, MD (General Medicine)'), ('SPECIALIZATION', 'General Physician'), ('EXPERIENCE', '12+ years'), ('LANGUAGES', 'English, Telugu, Hindi'),
                         ('CONSULTATION FEE', '₹300 per consultation'), ('MEDICAL REGISTRATION', 'TSMC-45678'), ('HOSPITAL / CLINIC', 'Sri Sai Hospital'), ('ADDRESS', '12-4, MG Road, Ameerpet')]:
            ok(f'profile shows {lab.lower()}: {val}', lab in t.upper() and val in t, '')
        ok('verified badge with the registration number', 'Verified by Healvio' in t and 'TSMC-45678' in t)
        ok('about the doctor', 'About Dr.' in t or 'About' in t and 'fever, diabetes' in t)
        ok('Instagram-style header: photo ring + years / rating / fee', P.locator('.dring .av').count() == 1 and '12+' in t and '5.0★' in t and '₹300' in t)
        ok('Google map of the hospital area is shown', P.locator('iframe.mapframe').count() == 1 and any('Sri%20Sai%20Hospital' in u and 'Ameerpet' in u and 'Hyderabad' in u for u in maps), maps[:1])
        ok('Directions opens Google Maps to the hospital', P.locator('a[href^="https://www.google.com/maps/dir/?api=1&destination=Sri%20Sai%20Hospital"]').count() == 1)
        ok('timings: today, open now, slot length', 'Today: 12:00 AM – 11:59 PM' in t and 'Open now' in t and 'Each consultation today is 15 minutes' in t, t[t.find('Timings'):t.find('Timings')+200])
        days = P.evaluate("[...document.querySelectorAll('.avweek .avday')].map(x => x.innerText.replace(/\\n/g,' '))")
        ok('next 7 days shown, Sunday is a day off', len(days) == 7 and sum('Day off' in x for x in days) == 1 and any(x.startswith('Sun') and 'Day off' in x for x in days), days)
        ok('reviews: average and star bars', P.locator('.rbar').count() == 5 and 'Very clear and kind.' in t)
        P.evaluate("document.querySelector('main').scrollTop = 700"); W(P, 300)
        P.screenshot(path='dr02_profile_mid.png')
        P.evaluate("document.querySelector('main').scrollTop = 1500"); W(P, 300)
        P.screenshot(path='dr03_profile_bottom.png')
        # zoom from the profile
        P.evaluate("document.querySelector('main').scrollTop = 0"); W(P, 200)
        P.evaluate("state.confirm = null; state.modal = null; render()"); W(P, 200)
        P.click('.dring'); W(P, 400)
        ok('profile photo opens full screen with name', P.locator('#zoom-ov img').count() == 1 and 'Dr. Ananya Rao' in P.locator('#zoom-ov .zcap').inner_text())
        box = P.locator('#zoom-ov .zstage').bounding_box()
        cx, cy = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
        P.mouse.click(cx, cy); P.wait_for_timeout(120); P.mouse.click(cx, cy); W(P, 400)
        ok('double-tap zooms in', 'scale(2.6)' in (P.locator('#zoom-ov img').get_attribute('style') or ''), P.locator('#zoom-ov img').get_attribute('style'))
        P.screenshot(path='dr04_zoom.png')
        P.mouse.move(cx, cy); P.mouse.down(); P.mouse.move(cx + 60, cy + 40, steps=5); P.mouse.up(); W(P, 300)
        st = P.locator('#zoom-ov img').get_attribute('style') or ''
        ok('drag moves the zoomed photo', 'scale(2.6)' in st and 'translate(0px, 0px)' not in st, st)
        P.mouse.click(cx, cy); P.wait_for_timeout(120); P.mouse.click(cx, cy); W(P, 400)
        ok('double-tap again zooms out', 'scale(1)' in (P.locator('#zoom-ov img').get_attribute('style') or ''))
        P.mouse.move(cx, cy); P.mouse.down(); P.mouse.move(cx, cy + 200, steps=6); P.mouse.up(); W(P, 400)
        ok('swipe down closes the photo', P.locator('#zoom-ov').count() == 0)
        # pinch with two touch points (simulated pointers)
        P.click('.dring'); W(P, 400)
        P.evaluate("""(() => { const st = document.querySelector('#zoom-ov .zstage'), r = st.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
          const ev = (type, id, x) => st.dispatchEvent(new PointerEvent(type, { pointerId: id, clientX: x, clientY: cy, bubbles: true, pointerType: 'touch' }));
          ev('pointerdown', 1, cx - 40); ev('pointerdown', 2, cx + 40); ev('pointermove', 1, cx - 100); ev('pointermove', 2, cx + 100); ev('pointerup', 1, cx - 100); ev('pointerup', 2, cx + 100); })()"""); W(P, 300)
        sc = P.evaluate("(document.querySelector('#zoom-ov img').style.transform.match(/scale\\(([\\d.]+)\\)/) || [0, 0])[1]")
        ok('pinch zooms (2 fingers apart → bigger)', float(sc) > 2.2, sc)
        P.click('#zoom-ov .zx'); W(P, 300)
        # long button labels are never cut
        P.evaluate("go('rxView', { id: Object.keys(Store.data.prescriptions)[0] || 'x' })"); W(P, 400)
        cut = P.evaluate("[...document.querySelectorAll('.btn')].filter(b => b.offsetParent && b.scrollWidth > b.clientWidth + 1).map(b => b.textContent.trim())")
        ok('no button text is cut anywhere on screen', cut == [], cut)
        print('denied:', denied(P))
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
