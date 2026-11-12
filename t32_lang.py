import re, json, subprocess, time
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8106'))
KEY = 'BKrC6jePyiPug3DIb-xAkQ8G0MuJuvwQq6-jZQesTtZC5s908ulwrRZqFUyyiZPDiAuRyMGOOfDsKEygQppBETY'
CFG = CFG.replace('VAPID-KEY', KEY)
SEED['requests/r1'] = {**SEED['requests/r1'], 'status': 'completed', 'endedAt': T, 'rateSkipped': True, 'rxId': 'rx1'}
ai_log, ai_mode = [], {'v': 'ok'}
def ai_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    b = json.loads(route.request.post_data or '{}'); p = b.get('prompt', '')
    ai_log.append(p[:120])
    if ai_mode['v'] == 'limit': return j(route, {'error': 'free_limit'}, 429)
    m = re.search(r'Items:\n(\[.*\])', p, re.S)
    if m:
        items = json.loads(m.group(1))
        return j(route, {'text': json.dumps(['తె:' + x for x in items], ensure_ascii=False)})
    if '"text"' in p: return j(route, {'text': json.dumps({'text': 'తెలుగులో చదవండి'}, ensure_ascii=False)})
    return j(route, {'text': '{}'})
def push_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    j(route, {'sent': 1, 'phones': 1})
def txt(p, sel='body'): return p.evaluate("(s) => { const e = document.querySelector(s); return e ? e.innerText : ''; }", sel)
LATIN_LEFT = r"""(() => {   // English words still on screen (names, brand words and numbers are fine)
  const ok = /^(Healvio|PayPal|Google|Google Maps|AI|ID|A–Z|OK|Install app|Notifications|Allow|Chrome|Tele-MANAS|mg|ml|tab|video|×|—|·|am|pm|AM|PM)$/;
  const out = new Set(); const w = document.createTreeWalker(document.getElementById('app'), NodeFilter.SHOW_TEXT);
  while (w.nextNode()) { const n = w.currentNode, p = n.parentElement; if (!p || p.closest(I18N.SKIP)) continue;
    const v = n.nodeValue.replace(/\s+/g, ' ').trim(); if (!/[A-Za-z]{3,}/.test(v)) continue;
    const words = v.replace(/[^A-Za-z\- ]/g, ' ').split(/\s+/).filter(x => x.length > 2 && !ok.test(x));
    if (words.length && !v.startsWith('తె:')) out.add(v.slice(0, 60)); }
  return [...out];
})()"""
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
        ctx.route('https://w.healvio.test/', ai_route)
        D = ctx.new_page(); D.on('pageerror', lambda e: errs.append(('D', str(e)))); D.goto(URL); W(D, 1400)
        P = ctx.new_page(); P.on('pageerror', lambda e: errs.append(('P', str(e)))); P.goto(URL); W(P, 1400)
        seed(D); W(D, 400)
        D.evaluate(f"globalThis.__googleEmail={json.dumps(DOC_E)}; globalThis.__googleName='Ananya Rao'"); D.click('button:has-text("Continue with Google")'); W(D, 1300)
        P.evaluate(f"globalThis.__noLangAsk = false; globalThis.__googleEmail={json.dumps(PAT_E)}; globalThis.__googleName='Ravi Kumar'"); P.click('button:has-text("Continue with Google")'); W(P, 1800)
        ok('after login the patient is asked to choose a language', P.locator('.modal:has-text("Choose your language")').count() == 1 and P.locator('.langbtn').count() == 12, P.locator('.langbtn').count())
        P.screenshot(path='/tmp/lang_pick.png')
        ok('language names are shown in their own script', all(x in txt(P, '.modal') for x in ['తెలుగు', 'हिन्दी', 'தமிழ்', 'ಕನ್ನಡ', 'മലയാളം', 'मराठी', 'বাংলা', 'ગુજરાતી', 'ਪੰਜਾਬੀ', 'ଓଡ଼ିଆ', 'اردو']))
        P.click('.langbtn[data-v="Telugu"]'); W(P, 1500)
        nav = P.evaluate("[...document.querySelectorAll('nav .tab, .tabbar .tab, .tab')].map(e => e.innerText.trim()).filter(Boolean).slice(0, 5)")
        ok('the whole app turns into Telugu (bottom tabs)', 'డాక్టర్లు' in nav and any('కన్సల్ట్స్' in x for x in nav) and 'ప్రొఫైల్' in nav, nav)
        home = txt(P, 'main')
        ok('home screen in Telugu', 'అత్యవసర ముందస్తు బుకింగ్' in home and 'ఏ డాక్టర్ కావాలో తెలియట్లేదా' in home, home[:300])
        ok('search box hint in Telugu', 'వెతకండి' in (P.get_attribute('#q', 'placeholder') or ''), P.get_attribute('#q', 'placeholder'))
        ok('choice saved on the account (works on any phone)', P.evaluate(f"globalThis.__fsStore.get('accounts/{PAT}').appLang") == 'Telugu')
        W(P, 2500)
        ok('names and other details are turned by AI (shared word list first, AI only for the rest)', len(ai_log) >= 1 and 'తె:' in txt(P, 'main'), (len(ai_log), txt(P, 'main')[:200]))
        P.screenshot(path='/tmp/lang_home_te.png')
        # typing is not changed
        P.fill('#q', 'Ananya'); W(P, 800)
        ok('what the patient types is never changed', P.input_value('#q') == 'Ananya')
        P.fill('#q', ''); W(P, 400)
        # consultation list: dates in Telugu month names
        P.evaluate("root('pConsults'); state.tab.pc = 'past'; render()"); W(P, 1500)
        pc = txt(P, 'main')
        ok('consultations screen in Telugu', 'నా కన్సల్టేషన్లు' in txt(P, 'body') and 'గతం' in pc, pc[:300])
        P.evaluate("go('consult', { id: 'r2' })"); W(P, 1500)
        cv = txt(P, 'main')
        ok('dates use Telugu month names (no "Nov")', 'Nov' not in cv and ('నవం' in cv or 'నవ' in cv), cv[:500])
        # prescription: everything turned, medicine names too (by AI)
        P.evaluate("go('rxView', { id: 'rx1' })"); W(P, 3500)
        rx = txt(P, 'main')
        ok('prescription in Telugu, medicine names turned too', 'తె:Paracetamol' in rx or 'తె:ORS' in rx, rx[:600])
        ok('prescription headings in Telugu', 'ప్రిస్క్రిప్షన్' in txt(P, 'body'), txt(P, 'body')[:200])
        P.screenshot(path='/tmp/lang_rx_te.png', full_page=True)
        P.evaluate("Speak.ok = () => true; Speak.say = (k, t, l) => { window.__said = [t, l]; }"); P.click('[data-act="speakRx"]'); W(P, 1500)
        ok('"read aloud" reads the prescription in Telugu', P.evaluate("window.__said && window.__said[1]") == 'Telugu', P.evaluate("window.__said"))
        # the store still gets English
        ok('stored prescription data stays English (pharmacy reads it)', P.evaluate("Store.data.prescriptions.rx1.medicines[0].name") == 'Paracetamol 650')
        # profile: change language
        P.evaluate("root('profile')"); W(P, 1000)
        ok('profile shows the app language (in its own script)', 'యాప్ భాష' in txt(P, 'main') and 'తెలుగు' in txt(P, 'main'), txt(P, 'main')[:300])
        # doctor stays English
        D.evaluate("root('dQueue')"); W(D, 800)
        ok('doctor screens stay in English', "Today's availability" in txt(D, 'main') and not re.search('[ఀ-౿]', txt(D, 'body')), txt(D, 'main')[:200])
        # leftovers
        P.evaluate("root('pHome')"); W(P, 2500)
        left = P.evaluate(LATIN_LEFT)
        print('   English text still on home:', left[:15])
        ok('no English words left on the home screen (the rest was turned by AI)', len(left) == 0, left)
        ok('avatars, the brand name and short codes are never sent to AI', not any(re.search(r'"(AR|RK|Healvio|PayPal)"', x) for x in ai_log) and 'తె:AR' not in txt(P, 'body'), [x for x in ai_log if 'Healvio"' in x][:2])
        # reload: stays Telugu, from the saved word list
        P.reload(); W(P, 2000)
        P.evaluate(f"globalThis.__googleEmail={json.dumps(PAT_E)}; globalThis.__googleName='Ravi Kumar'")
        if P.locator('button:has-text("Continue with Google")').count(): P.click('button:has-text("Continue with Google")'); W(P, 1800)
        P.evaluate("state.modal = null; render()"); W(P, 800)
        ok('after reopening the app it is still Telugu', 'డాక్టర్లు' in txt(P, 'body') and P.evaluate("I18N.lang") == 'Telugu')
        # Urdu and Hindi
        P.evaluate("ACT.setLang({ v: 'Hindi' })"); W(P, 1500)
        ok('Hindi works', 'डॉक्टर' in txt(P, 'body') and 'आपात प्री-बुकिंग' in txt(P, 'main'), txt(P, 'main')[:200])
        P.evaluate("ACT.setLang({ v: 'Urdu' })"); W(P, 1500)
        ok('Urdu works', 'ڈاکٹرز' in txt(P, 'body'), txt(P, 'body')[:200])
        # AI limit reached: fixed words still turned, nothing breaks, no endless retries
        ai_mode['v'] = 'limit'; n0 = len(ai_log)
        P.evaluate("ACT.setLang({ v: 'Tamil' })"); W(P, 4000)
        ok('AI limit reached: app words still in Tamil, names stay as they are', 'மருத்துவர்கள்' in txt(P, 'body') and len(ai_log) - n0 <= 6, len(ai_log) - n0)
        ai_mode['v'] = 'ok'
        # back to English
        P.evaluate("ACT.setLang({ v: 'English' })"); W(P, 1500)
        ok('back to English: no Indian-language text left', 'Doctors' in txt(P, 'body') and not re.search('[ऀ-෿؀-ۿ]', txt(P, 'main')), txt(P, 'main')[:200])
        ok('English choice saved on the account', P.evaluate(f"globalThis.__fsStore.get('accounts/{PAT}').appLang") == 'English')
        bad = [x for x in P.evaluate('globalThis.__denied') if not x.startswith('listen')]
        ok('no refused saves', not bad, bad)
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
