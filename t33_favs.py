import re, json, subprocess, time
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8107'))
KEY = 'BKrC6jePyiPug3DIb-xAkQ8G0MuJuvwQq6-jZQesTtZC5s908ulwrRZqFUyyiZPDiAuRyMGOOfDsKEygQppBETY'
CFG = CFG.replace('VAPID-KEY', KEY)
SEED['requests/r1'] = {**SEED['requests/r1'], 'status': 'completed', 'endedAt': T, 'rateSkipped': True}
AD_E = 'hmc.info112@gmail.com'; AD = gid(AD_E)
P2_E = 'second.patient@example.com'; P2 = gid(P2_E)
D2 = 'gdrsuresh'
doc2 = {**docinfo, 'specialization': 'General Physician', 'system': 'Allopathy', 'hospital': 'City Clinic'}
SEED.update({
    f'accounts/{AD}': {'id': AD, 'role': 'patient', 'name': 'HMC', 'email': AD_E, 'status': 'active', 'createdAt': T},
    f'admins/{AD}': {'note': 'owner'},
    f'accounts/{P2}': {'id': P2, 'role': 'patient', 'name': 'Second Patient', 'email': P2_E, 'status': 'active', 'createdAt': T},
    f'accounts/{D2}': {'id': D2, 'role': 'doctor', 'name': 'Suresh Varma', 'email': 'dr.suresh@example.com', 'status': 'approved', 'createdAt': T, 'approvedAt': T, 'doc': {**doc2, 'docFiles': []}},
    f'public/{D2}': {'id': D2, 'role': 'doctor', 'name': 'Suresh Varma', 'status': 'approved', 'demo': False, 'doc': doc2},
    'complaints/cp1': {'id': 'cp1', 'by': PAT, 'byName': 'Ravi Kumar', 'role': 'patient', 'ref': {'kind': 'consult', 'id': 'r2'}, 'against': DOC, 'category': 'doctor', 'text': 'Rude and gave wrong advice', 'status': 'open', 'at': T},
})
push_log = []
def push_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    push_log.append(json.loads(route.request.post_data)); j(route, {'sent': 1, 'phones': 1})
def txt(p, sel='main'): return p.evaluate("(s) => { const e = document.querySelector(s); return e ? e.innerText : ''; }", sel)
def favs(p, uid): return [f['id'] for f in (p.evaluate("(k) => (globalThis.__fsStore.get(k) || {}).favDocs || []", 'accounts/' + uid))]
def notes_to(p, uid): return p.evaluate("(u) => [...globalThis.__fsStore.values()].filter(v => v && v.to === u && v.text).map(v => [v.title || '', v.text])", uid)
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, geolocation=HOME, permissions=['geolocation', 'notifications'])
        def mk(f):
            body = open(f'fs_{f}.js').read()
            return lambda r: r.fulfill(status=200, content_type='application/javascript', headers={'Access-Control-Allow-Origin': '*'}, body=body)
        ctx.route(re.compile(r'https://fonts\..*'), lambda r: r.abort())
        for mod, f in [('app', 'app'), ('firestore', 'firestore_shared'), ('auth', 'auth'), ('messaging', 'messaging')]:
            ctx.route(f'https://www.gstatic.com/firebasejs/{V}/firebase-{mod}.js', mk(f))
        ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
        ctx.route(re.compile(r'https://w\.healvio\.test/status(\?.*)?$'), lambda r: j(r, status))
        ctx.route('https://w.healvio.test/push', push_route)
        P = ctx.new_page(); P.on('pageerror', lambda e: errs.append(('P', str(e)))); P.goto(URL); W(P, 1400)
        A = ctx.new_page(); A.on('pageerror', lambda e: errs.append(('A', str(e)))); A.goto(URL); W(A, 1400)
        seed(P); W(P, 400)
        P.evaluate(f"globalThis.__googleEmail={json.dumps(PAT_E)}; globalThis.__googleName='Ravi Kumar'"); P.click('button:has-text("Continue with Google")'); W(P, 1500)
        A.evaluate(f"globalThis.__googleEmail={json.dumps(AD_E)}; globalThis.__googleName='HMC'"); A.click('button:has-text("Continue with Google")'); W(A, 1500)
        for p in (P, A): p.evaluate("state.confirm = null; state.modal = null; state.sheet = null; render()"); W(p, 200)
        P.evaluate("root('pHome')"); W(P, 500)
        ok('no "My doctors" section before saving anyone', '♥ My doctors' not in txt(P))
        ok('every doctor card has a heart to save the doctor', P.locator('.dcard .favh').count() == 2, P.locator('.dcard .favh').count())
        P.click(f'.card:has-text("Ananya Rao") .favh'); W(P, 1200)
        ok('tapping the heart saves the doctor (and does not open the profile)', favs(P, PAT) == [DOC] and P.evaluate("state.view") == 'pHome', (favs(P, PAT), P.evaluate("state.view")))
        ok('"Saved to My doctors." message', 'Saved to My doctors.' in txt(P, '#toast'))
        t = txt(P)
        ok('"My doctors" appears on the home screen with the doctor', '♥ My doctors' in t and P.locator('.favcard:has-text("Ananya Rao")').count() == 1, t[:300])
        P.evaluate(f"go('pDoctor', {{ id: '{D2}' }})"); W(P, 700)
        ok('doctor profile shows "Save as my doctor"', '♡ Save as my doctor' in txt(P))
        P.click('button:has-text("Save as my doctor")'); W(P, 1200)
        ok('saved from the profile; the button now says "My doctor"', favs(P, PAT) == [D2, DOC] and '♥ My doctor' in txt(P), favs(P, PAT))
        P.evaluate("root('pHome')"); W(P, 600)
        ok('as many doctors as you like: both are in My doctors', P.locator('.favcard').count() == 2)
        P.click('.chip:has-text("My doctors")'); W(P, 500)
        ok('"♥ My doctors" filter shows only saved doctors', P.locator('.dcard').count() == 2)
        P.evaluate("state.filters.fav = false; render()"); W(P, 300)
        P.screenshot(path='/tmp/fav_home.png')
        P.click('.favcard:has-text("Suresh")'); W(P, 700)
        ok('tapping a saved doctor opens their profile to book', P.evaluate("state.view") == 'pDoctor' and P.evaluate("state.params.id") == D2)
        P.click('button:has-text("My doctor")'); W(P, 1000)
        ok('tap again to remove', favs(P, PAT) == [DOC] and 'Removed from My doctors.' in txt(P, '#toast'), favs(P, PAT))
        P.click('button:has-text("Save as my doctor")'); W(P, 1000)
        ok('saved again', set(favs(P, PAT)) == {DOC, D2})
        # admin terminates a saved doctor after a patient report
        A.evaluate("state.admin = true; LS.set('healvio:admin','1'); state.stack = []; root('aDoctors')"); W(A, 900)
        A.evaluate(f"go('aDoctor', {{ id: '{DOC}' }})"); W(A, 800)
        A.click('button:has-text("Terminate doctor")'); W(A, 600)
        mt = txt(A, '.modal')
        ok('admin is told how many patients saved this doctor', '1 patient has saved this doctor and will be told' in mt, mt)
        ok('"because of a patient report" is ticked by itself (a report exists)', A.is_checked('#cf-check'))
        A.screenshot(path='/tmp/fav_admin.png')
        A.fill('#cf-reason', 'Serious patient complaint confirmed'); A.click('.modal button:has-text("Terminate")'); W(A, 1800)
        n = notes_to(A, PAT)
        rem = [x for x in n if x[0] == 'Your saved doctor was removed']
        ok('patient who saved the doctor is told: removed after a patient report', len(rem) == 1 and 'Dr. Ananya Rao' in rem[0][1] and 'removed from Healvio after a patient report' in rem[0][1], rem)
        ok("their phone rings", any(x.get('to') == PAT for x in push_log), push_log[-3:])
        ok('a patient who did not save the doctor is not told', not [x for x in notes_to(A, P2) if 'saved doctor' in x[0]])
        ok('admin toast says the patients were told', '1 patient who saved this doctor was told' in txt(A, '#toast'), txt(A, '#toast'))
        W(P, 900); P.evaluate("root('alerts')"); W(P, 800)
        ok('patient sees the alert in the app (Alerts)', 'removed from Healvio after a patient report' in txt(P, 'main'), txt(P, 'main')[:300])
        P.evaluate("root('pHome')"); W(P, 800)
        g = txt(P, '.favrow')
        ok('in My doctors the doctor shows "No longer on Healvio" with Remove', 'No longer on Healvio' in g and 'Remove' in g, g)
        ok('the terminated doctor is not in the doctor list any more', P.locator('.dcard:has-text("Ananya")').count() == 0)
        P.screenshot(path='/tmp/fav_gone.png')
        # reinstated → told it is back
        A.evaluate(f"go('aDoctor', {{ id: '{DOC}' }})"); W(A, 600)
        A.click('button:has-text("Reinstate")'); A.click('.modal button:has-text("Reinstate")'); W(A, 1800)
        back = [x for x in notes_to(A, PAT) if x[0] == 'Your saved doctor is back']
        ok('reinstated: the patient is told the doctor is back', len(back) == 1 and 'available on Healvio again' in back[0][1], back)
        W(P, 800); P.evaluate("render()"); W(P, 300)
        ok('My doctors shows the doctor normally again', 'No longer on Healvio' not in txt(P, '.favrow') and P.locator('.favcard:has-text("Ananya")').count() == 1)
        # terminated for another reason (not a report)
        A.evaluate(f"go('aDoctor', {{ id: '{D2}' }})"); W(A, 600)
        A.click('button:has-text("Terminate doctor")'); W(A, 500)
        ok('no report about this doctor: the box is not ticked', not A.is_checked('#cf-check'))
        A.fill('#cf-reason', 'Licence expired'); A.click('.modal button:has-text("Terminate")'); W(A, 1800)
        other = [x[1] for x in notes_to(A, PAT) if x[0] == 'Your saved doctor was removed' and 'Suresh' in x[1]]
        ok('other reasons: "no longer available", without blaming a report', len(other) == 1 and 'no longer available on Healvio' in other[0] and 'report' not in other[0], other)
        # remove the gone doctor
        W(P, 800); P.evaluate("render()"); W(P, 300)
        P.click('.favcard.gone button:has-text("Remove")'); W(P, 1000)
        ok('a removed doctor can be taken out of My doctors', favs(P, PAT) == [DOC], favs(P, PAT))
        # in the patient's language
        P.evaluate("ACT.setLang({ v: 'Telugu' })"); W(P, 1500)
        ok('My doctors in Telugu', '♥ నా డాక్టర్లు' in txt(P), txt(P)[:200])
        P.evaluate("ACT.setLang({ v: 'English' })"); W(P, 800)
        bad = [x for x in P.evaluate('globalThis.__denied') + A.evaluate('globalThis.__denied') if not x.startswith('listen')]
        ok('no refused saves', not bad, bad)
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
