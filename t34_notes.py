# Alerts in the patient's app language (Alerts list, in-app pop-up, language pack for phone pop-ups)
import re, json, subprocess, time
from playwright.sync_api import sync_playwright
src32 = open('t32_lang.py').read()
exec(src32[:src32.index("try:\n    with sync_playwright")].replace('8106', '8108'))
LANGS = ['Telugu', 'Hindi', 'Tamil', 'Kannada', 'Malayalam', 'Marathi', 'Bengali', 'Gujarati', 'Punjabi', 'Odia', 'Urdu']
SCRIPT = {'Telugu': '[ఀ-౿]', 'Hindi': '[ऀ-ॿ]', 'Tamil': '[஀-௿]', 'Kannada': '[ಀ-೿]', 'Malayalam': '[ഀ-ൿ]', 'Marathi': '[ऀ-ॿ]', 'Bengali': '[ঀ-৿]',
          'Gujarati': '[઀-૿]', 'Punjabi': '[਀-੿]', 'Odia': '[଀-୿]', 'Urdu': '[؀-ۿ]'}
# every alert a patient can get, built with the app's own helpers (same text as the real alerts)
NOTES_JS = r"""(() => {
  const d = A(DOC_ID), dr = drName(d), fee = money(500), slot = `${fmtDay(today())}, ${t12('10:30')}`, later = `${fmtDate(addDays(today(), 3))}, ${t12('16:00')}`;
  return [
    ['acc', `✅ ${dr} accepted your request. Your slot: ${slot}. Please pay the ${fee} fee in the app to confirm it. The consultation starts after payment.`],
    ['wait', `You're #2 on ${dr}'s waiting list. Expected connection: ${later}. Pay the ${fee} fee in the app so the doctor can connect you on time.`],
    ['done', `Your consultation with ${dr} is complete. Please rate your experience.`],
    ['cxl', `${dr} cancelled your appointment: Emergency surgery today. Your fee was refunded to your PayPal account.`],
    ['dly', `⏳ ${dr} is running about 10 minutes late. Your consultation is now expected at about ${t12('10:40')} (booked for ${t12('10:30')}). We'll alert you when the doctor is ready.`],
    ['order', `Sri Sai Medicals: 2 of 3 medicines are available and kept ready. Total ${money(1240)}. Pay in the app with PayPal, or cash at the door. Note: Cetirizine is out of stock`],
    ['way', `🛵 Your medicines from Sri Sai Medicals are on the way with Kiran. Open Healvio to track live.`],
    ['saved', `⚠️ ${dr}, one of your saved doctors, was removed from Healvio after a patient report. Please choose another doctor for your next consultation.`],
    ['chat', `${dr}: Cheyadaniki ready ga undandi`, { view: 'room', id: 'r1' }],
    ['old', `${dr} is ready for you now. Open the consult room to connect.`, { view: 'room', id: 'r1' }],
    ['miss', `Missed video call from ${dr}`, { view: 'room', id: 'r1' }],
    ['other', 'Something brand new happened.']
  ].map(([k, text, ref], i) => ({ id: 'nt-' + k, to: state.me, text, ref: ref || { view: 'consult', id: 'r1' }, kind: 'info', at: now() - (i + 1) * 60000, read: true }));
})()"""
def samples(p):  # one filled example of every pattern
    return p.evaluate(r"""NOTE_TPL.map(en => en.replace(/\{(\w+)\}/g, (m, k) => ({ dr: 'Dr. Ananya Rao', name: 'Ravi Kumar', store: 'Sri Sai Medicals', rider: 'Kiran', money: '₹500', time: '10:30 AM', time2: '10:20 AM',
      n: '3', n2: '5', date: 'Today', text: 'Doctor is unwell', q: 'Thank you so much' })[k]))""")
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
        P.evaluate(f"globalThis.__googleEmail={json.dumps(PAT_E)}; globalThis.__googleName='Ravi Kumar'"); P.click('button:has-text("Continue with Google")'); W(P, 1800)
        P.evaluate("ACT.setLang({ v: 'Telugu' })"); W(P, 1800)
        ok('the patient chose Telugu', P.evaluate("I18N.lang") == 'Telugu' and P.evaluate("I18N.on()"))
        notes = P.evaluate(NOTES_JS.replace('DOC_ID', json.dumps(DOC)))
        P.evaluate("ns => Promise.all(ns.map(n => Store.put('notifications', { ...n, from: state.me })))", notes); W(P, 600)
        P.evaluate("root('alerts')"); W(P, 1500)
        cards = P.evaluate("[...document.querySelectorAll('main .card[data-act=openNote]')].map(c => [c.dataset.id, c.querySelector('.small').innerText])")
        C = dict(cards)
        P.screenshot(path='/tmp/alerts_te.png', full_page=True)
        dr = P.evaluate(f"drName(A({json.dumps(DOC)}))")
        te = lambda s: bool(re.search('[ఀ-౿]', s or ''))
        ok('Alerts title in Telugu', 'అలర్ట్స్' in txt(P, 'body'), txt(P, 'body')[:80])
        ok('"request accepted" alert in Telugu, with the pay sentence', te(C.get('nt-acc')) and 'అంగీకరించారు' in C['nt-acc'] and 'ఫీజు' in C['nt-acc'] and 'accepted' not in C['nt-acc'], C.get('nt-acc'))
        ok('doctor name, price and time stay as written; "Today" in Telugu', dr in C['nt-acc'] and '₹500' in C['nt-acc'] and '10:30 AM' in C['nt-acc'] and 'ఈరోజు' in C['nt-acc'] and 'Today' not in C['nt-acc'], C['nt-acc'])
        ok('waiting list alert: date shown with a Telugu month name', te(C.get('nt-wait')) and not re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b', C['nt-wait']) and '#2' in C['nt-wait'], C.get('nt-wait'))
        ok('"consultation complete" alert (the one in your photo) in Telugu', te(C.get('nt-done')) and 'పూర్తయింది' in C['nt-done'] and 'Please rate' not in C['nt-done'], C.get('nt-done'))
        ok('doctor cancelled: the reason they typed stays, the rest in Telugu', 'Emergency surgery today' in C['nt-cxl'] and te(C['nt-cxl']) and 'refunded' not in C['nt-cxl'], C['nt-cxl'])
        ok('"running late" alert in Telugu', te(C.get('nt-dly')) and 'ఆలస్యంగా' in C['nt-dly'] and '10:40 AM' in C['nt-dly'], C.get('nt-dly'))
        ok('store answer: every sentence in Telugu, the store\'s note kept as typed', te(C['nt-order']) and 'Sri Sai Medicals' in C['nt-order'] and 'Cetirizine is out of stock' in C['nt-order'] and not re.search(r'available|Total|cash at', C['nt-order']), C['nt-order'])
        ok('delivery alert in Telugu, rider name kept', te(C['nt-way']) and 'Kiran' in C['nt-way'] and 'on the way' not in C['nt-way'], C['nt-way'])
        ok('saved doctor removed alert in Telugu', te(C['nt-saved']) and 'తొలగించారు' in C['nt-saved'], C['nt-saved'])
        ok('chat messages: the words stay exactly as the doctor typed them (never sent to AI)', (C.get('nt-chat') or '').endswith(': Cheyadaniki ready ga undandi') and not any('Cheyadaniki' in x for x in ai_log), C.get('nt-chat'))
        ok('an older wording ("ready… Open the consult room to connect", saved as a consult-room alert like the real one) is in Telugu too', te(C.get('nt-old')) and 'Open the consult room' not in C['nt-old'], C.get('nt-old'))
        ok('missed call alert from the consult room in Telugu', te(C.get('nt-miss')) and 'Missed' not in C['nt-miss'], C.get('nt-miss'))
        W(P, 3000)  # names go to AI once (the fake AI writes తె: before them), then the alerts are drawn again
        C = dict(P.evaluate("[...document.querySelectorAll('main .card[data-act=openNote]')].map(c => [c.dataset.id, c.querySelector('.small').innerText])"))
        ok('doctor names in alerts are in the chosen language, like the doctor list', C.get('nt-done', '').startswith('తె:' + dr) and ('తె:' + dr) in C.get('nt-acc', ''), [C.get('nt-done'), C.get('nt-acc', '')[:60]])
        ok('store and rider names too', 'తె:Sri Sai Medicals' in C.get('nt-way', '') and 'తె:Kiran' in C.get('nt-way', ''), C.get('nt-way'))
        ok('chat alert: the sender\'s name in Telugu, the message as typed', C.get('nt-chat') == f'తె:{dr}: Cheyadaniki ready ga undandi', C.get('nt-chat'))
        ok('older "ready" alert: the doctor name in Telugu too', C.get('nt-old', '').startswith('తె:' + dr) and te(C['nt-old'].replace('తె:', '')), C.get('nt-old'))
        ok('an alert with no pattern still works (AI turns it, like before)', 'Something brand new' in C.get('nt-other', '') or C.get('nt-other', '').startswith('తె:'), C.get('nt-other'))
        ok('time labels ("7 h ago") still in Telugu', 'క్రితం' in txt(P, 'main'), txt(P, 'main')[-200:])
        # a new alert arrives while the app is open: the pop-up inside the app is in Telugu
        P.evaluate(f"""Store.put('notifications', {{ id: 'nt-new', to: state.me, from: state.me, text: `▶️ ${{drName(A({json.dumps(DOC)}))}} has started your consultation. Open the consult room to join.`, ref: {{ view: 'room', id: 'r1' }}, kind: 'urgent', at: now(), read: false }})""")
        W(P, 900)
        toast = txt(P, '#toast')
        ok('a new alert pops up inside the app in Telugu', te(toast) and 'ప్రారంభించారు' in toast and dr in toast, toast)
        # phone pop-ups: the service worker gets the same patterns
        pk = P.evaluate("caches.open('healvio-lang').then(c => c.match(location.href.replace(/[?#].*$/, '').replace(/[^/]*$/, '') + '__lang')).then(r => r ? r.json() : null)")
        ok('names saved for phone pop-ups too', pk and pk.get('names', {}).get(dr) == 'తె:' + dr, pk and list(pk.get('names', {}).items())[:3])
        ok('language saved for phone pop-ups (Telugu, every pattern)', pk and pk['on'] and pk['lang'] == 'Telugu' and len(pk['tpl']) == P.evaluate("NOTE_TPL.length") and pk['words'].get('Request accepted') == 'అభ్యర్థన అంగీకరించబడింది', pk and [pk.get('lang'), len(pk.get('tpl', []))])
        # the doctor's alerts stay English
        D.evaluate(f"""Store.put('notifications', {{ id: 'nd-1', to: state.me, from: state.me, text: 'Ravi Kumar rated your consultation 5★.', ref: {{ view: 'consult', id: 'r1' }}, kind: 'info', at: now(), read: true }}).then(() => root('alerts'))"""); W(D, 1200)
        dtxt = txt(D, 'main')
        ok('doctor alerts stay in English', 'Ravi Kumar rated your consultation' in dtxt and not re.search('[ఀ-౿]', dtxt), dtxt[:200])
        dpk = D.evaluate("caches.open('healvio-lang').then(c => c.match(location.href.replace(/[?#].*$/, '').replace(/[^/]*$/, '') + '__lang')).then(r => r ? r.json() : null)")
        print('   (pack seen from the doctor page, same browser):', dpk and dpk.get('on'))
        # every pattern in every language
        S = samples(P)
        problems = []
        for lang in LANGS:
            P.evaluate(f"ACT.setLang({{ v: '{lang}' }})"); W(P, 1300)
            out = P.evaluate("ss => ss.map(s => I18N.note(s))", S)
            for s, o in zip(S, out):
                if not o: problems.append((lang, 'no translation', s[:50])); continue
                keep = [v for v in ['Dr. Ananya Rao', 'Ravi Kumar', 'Sri Sai Medicals', 'Kiran', '₹500', '10:30 AM', '10:20 AM', 'Doctor is unwell', 'Thank you so much'] if v in s]
                if any(v not in o for v in keep): problems.append((lang, 'lost a name/number', o[:60]))
                rest = o
                for v in keep + ['Healvio', 'PayPal', 'AM', 'PM']: rest = rest.replace(v, ' ')
                if re.search(r'[A-Za-z]{3,}', rest): problems.append((lang, 'English left', o[:70]))
                if not re.search(SCRIPT[lang], o): problems.append((lang, 'not in the script', o[:60]))
        ok(f'all {len(S)} alert patterns turn in all 11 languages, keeping names, prices and times', not problems, problems[:6])
        pk2 = P.evaluate("caches.open('healvio-lang').then(c => c.match(location.href.replace(/[?#].*$/, '').replace(/[^/]*$/, '') + '__lang')).then(r => r ? r.json() : null)")
        ok('changing the language updates the phone pop-ups too', pk2 and pk2['lang'] == 'Urdu', pk2 and pk2.get('lang'))
        P.evaluate("root('alerts')"); W(P, 1200)
        ok('Urdu alerts list', re.search('[؀-ۿ]', P.evaluate("document.querySelector('[data-id=nt-done] .small').innerText")) is not None)
        # back to English
        P.evaluate("ACT.setLang({ v: 'English' })"); W(P, 1500)
        C2 = dict(P.evaluate("[...document.querySelectorAll('main .card[data-act=openNote]')].map(c => [c.dataset.id, c.querySelector('.small').innerText])"))
        ok('back to English: alerts in English again', C2.get('nt-done') == f'Your consultation with {dr} is complete. Please rate your experience.', C2.get('nt-done'))
        pk3 = P.evaluate("caches.open('healvio-lang').then(c => c.match(location.href.replace(/[?#].*$/, '').replace(/[^/]*$/, '') + '__lang')).then(r => r ? r.json() : null)")
        ok('English: phone pop-ups go back to English', pk3 is not None and pk3.get('on') is False, pk3)
        bad = [x for x in P.evaluate('globalThis.__denied') if not x.startswith('listen')]
        ok('no refused saves', not bad, bad)
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
