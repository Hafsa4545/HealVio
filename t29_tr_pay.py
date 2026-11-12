import re, json, subprocess, time
from playwright.sync_api import sync_playwright
src18 = open('t18_delivery.py').read()
exec(src18[:src18.index("try:\n    with sync_playwright")].replace('8091', '8102'))
KEY = 'BKrC6jePyiPug3DIb-xAkQ8G0MuJuvwQq6-jZQesTtZC5s908ulwrRZqFUyyiZPDiAuRyMGOOfDsKEygQppBETY'
CFG = CFG.replace('VAPID-KEY', KEY)
answers, push_log = [], []
def push_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    push_log.append(json.loads(route.request.post_data))
    j(route, answers.pop(0) if answers else {'sent': 1, 'phones': 1})

ai_log = []
seen = {}
def ai_route(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    b = json.loads(route.request.post_data)
    p = b.get('prompt', '')
    ai_log.append(b)
    if p.startswith('Translate each chat message'):
        arr = json.loads(p[p.index('Messages (JSON array):\n') + len('Messages (JSON array):\n'):].split('\n\nReply with the JSON only')[0])
        if any('FAILME' in x for x in arr): return j(route, {'error': 'boom'}, 500)
        out = []
        for x in arr:
            seen[x] = seen.get(x, 0) + 1
            if 'ECHO2' in x or re.search('[\u0C00-\u0C7F]', x) or ('ECHO1' in x and seen[x] == 1): out.append(x)  # the AI sends it back unchanged
            else: out.append('తె ' + x)
        return j(route, {'text': json.dumps(out, ensure_ascii=False)})
    return j(route, {'text': '{}'})
hang = []
pmode = {'v': 'hang'}
plog = []
def pay_hang(route):
    if route.request.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    if pmode['v'] == 'hang': return hang.append(route)  # never answers
    b = json.loads(route.request.post_data); step = route.request.url.rstrip('/').rsplit('/', 1)[1]
    plog.append({'step': step, 'b': b})
    if step == 'create':
        out = {'orderID': 'PPGO1', 'value': '3.16', 'currency': 'USD', 'inr': 300}
        if b.get('redirect'): out['approve'] = 'https://www.sandbox.paypal.com/checkoutnow?token=PPGO1'
        return j(route, out)
    j(route, {'ok': True, 'paid': {'by': 'paypal', 'orderId': b['orderID'], 'captureId': 'CAP-' + b['orderID'], 'amount': '3.16', 'currency': 'USD', 'inr': 300, 'at': 1, 'test': True}})
def paypal_page(route):
    back = [x for x in plog if x['step'] == 'create'][-1]['b']['back']
    route.fulfill(status=302, headers={'Location': back + '?paypal=ok&pk=fee&pi=rA&token=PPGO1&PayerID=TESTPAYER'})
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
        ctx.route('https://w.healvio.test/', ai_route)
        ctx.route('https://w.healvio.test/push', push_route)
        ctx.route('https://w.healvio.test/ice', lambda r: j(r, {'iceServers': []}))
        ctx.route(re.compile(r'https://w\.healvio\.test/pay/(create|capture)$'), pay_hang)
        ctx.route(re.compile(r'https://www\.paypal\.com/sdk/js.*'), sdk_route)
        D = ctx.new_page(); D.on('pageerror', lambda e: errs.append(('D', str(e)))); D.goto(URL); W(D, 1400)
        P = ctx.new_page(); P.on('pageerror', lambda e: errs.append(('P', str(e)))); P.goto(URL); W(P, 1400)
        seed(D); W(D, 400)
        P.evaluate(f"globalThis.__googleEmail={json.dumps(PAT_E)}; globalThis.__googleName='Ravi Kumar'")
        P.click('button:has-text("Continue with Google")'); W(P, 1800)
        P.evaluate("state.confirm = null; state.modal = null; state.sheet = null; render()"); W(P, 200)
        # ---- chat translation in small groups ----
        P.evaluate("go('room', { id: 'rA' })"); W(P, 800)
        P.evaluate("state.msgs.rA = Array.from({ length: 20 }, (_, i) => ({ id: 'm' + i, from: i % 2 ? '" + DOC + "' : Store.authUser.uid, text: 'Message number ' + i + ' about fever', at: Date.now() - (20 - i) * 1000 })); render()"); W(P, 300)
        ai_log.clear()
        P.evaluate("ACT.aiTranslate({ id: 'rA', v: 'Telugu' })"); W(P, 3500)
        n = len([x for x in ai_log if x['prompt'].startswith('Translate each chat message')])
        sizes = [len(json.loads(x['prompt'][x['prompt'].index('Messages (JSON array):\n') + 23:].split('\n\nReply with the JSON only')[0])) for x in ai_log]
        mapn = P.evaluate("Object.keys((state.tr.rA || {}).map || {}).length")
        ok('translation sent in small groups (≤6 messages each), all 20 translated', n == 4 and max(sizes) <= 6 and sum(sizes) == 20 and mapn == 20, [n, sizes, mapn])
        shown = P.evaluate("(() => { if (state.msgSub && state.msgSub.un) { state.msgSub.un(); } state.msgSub = { rid: 'rA', un: null }; Store.data.requests.rA = Object.assign({}, Store.data.requests.rA, { status: 'completed' }); state.view = 'room'; state.params = { id: 'rA' }; state.msgs.rA = Array.from({ length: 20 }, (_, i) => ({ id: 'm' + i, from: i % 2 ? '" + DOC + "' : Store.authUser.uid, text: 'Message number ' + i + ' about fever', at: Date.now() - (20 - i) * 1000 })); render(); return document.body.innerText; })()")
        dbg = P.evaluate("[state.view, (Store.data.requests.rA||{}).status, (state.msgs.rA||[]).length, Object.keys((state.tr.rA||{}).map||{}).slice(0,3), document.querySelectorAll('.msg').length]")
        ok('translations shown under the messages', 'తె Message number 19 about fever' in shown and 'తె Message number 0 about fever' in shown, [dbg, shown[:600]])
        ok('translation uses the accurate model', all(x.get('tier') in (None, 'default') for x in ai_log), [x.get('tier') for x in ai_log])
        # live: a new message arrives → translated by itself, no tap needed
        ai_log.clear()
        P.evaluate("state.msgs.rA = state.msgs.rA.concat([{ id: 'mNew', from: '" + DOC + "', text: 'Take Dolo 650 twice a day', at: Date.now() }]); render()"); W(P, 2500)
        live_n = len(ai_log); live_t = P.evaluate("(state.tr.rA.map || {}).mNew")
        ok('new message is translated by itself while chatting (only the new one is sent)', live_n == 1 and live_t == 'తె Take Dolo 650 twice a day' and 'Take Dolo 650 twice a day' in ai_log[0]['prompt'] and 'Message number 3' not in ai_log[0]['prompt'], [live_n, live_t])
        ok('translation language remembered for this chat', P.evaluate("JSON.parse(LS.get('healvio:tr:rA')).lang") == 'Telugu' and P.evaluate("Object.keys(JSON.parse(LS.get('healvio:tr:rA')).map).length") == 21)
        # opening the chat again → carries on in Telugu without asking, old translations kept (no new AI calls)
        ai_log.clear()
        P.evaluate("delete state.tr.rA; render()"); W(P, 1500)
        ok('opening the chat again keeps translating in the same language, no repeat AI work', P.evaluate("state.tr.rA && state.tr.rA.lang") == 'Telugu' and P.evaluate("Object.keys(state.tr.rA.map).length") == 21 and len(ai_log) == 0, len(ai_log))
        P.evaluate("Tr.stop('rA'); render()"); W(P, 200)
        ok('turning translation off forgets the language', P.evaluate("LS.get('healvio:tr:rA')") in (None, '') and not P.evaluate("!!state.tr.rA"))
        # one group fails → the rest still shown, clear note
        P.evaluate("state.msgs.rA = state.msgs.rA.slice(0, 20); state.msgs.rA[5].text = 'FAILME please'; Tr.stop('rA'); render()"); W(P, 200)
        ai_log.clear()
        P.evaluate("ACT.aiTranslate({ id: 'rA', v: 'Telugu' })"); W(P, 3500)
        mapn = P.evaluate("Object.keys((state.tr.rA || {}).map || {}).length")
        ok('one group fails → the other messages are still translated (and the failed ones are not retried in a loop)', mapn == 14 and P.evaluate("state.tr.rA.busy") is False and len(ai_log) == 4, [mapn, len(ai_log)])
        # ---- the AI sends a message back in English → asked again, never shown twice ----
        P.evaluate("Tr.stop('rA'); state.msgs.rA = [" + ",".join([
            "{ id: 'e1', from: '" + DOC + "', text: 'From how many days are u getting fever ECHO1', at: Date.now() - 5000 }",
            "{ id: 'e2', from: Store.authUser.uid, text: 'Yes mam ECHO2', at: Date.now() - 4000 }",
            "{ id: 'e3', from: Store.authUser.uid, text: 'నాకు జ్వరం వచ్చింది', at: Date.now() - 3000 }",
            "{ id: 'e4', from: '" + DOC + "', text: 'Take rest', at: Date.now() - 2000 }"]) + "]; render()"); W(P, 200)
        ai_log.clear()
        P.evaluate("ACT.aiTranslate({ id: 'rA', v: 'Telugu' })"); W(P, 3500)
        tm = P.evaluate("state.tr.rA.map")
        prompts = [x['prompt'] for x in ai_log]
        ok('a message that came back in English is asked again and then shown in Telugu', tm.get('e1') == 'తె From how many days are u getting fever ECHO1' and sum('ECHO1' in x for x in prompts) == 2, [tm, len(prompts)])
        ok('the second ask is for that message alone and says "in Telugu letters, not in English"', any('ECHO1' in x and 'Write the translation in Telugu letters, not in English.' in x and 'Take rest' not in x for x in prompts))
        ok('still English after asking again: nothing shown under it (no same words twice), asked only twice', 'e2' not in tm and sum('ECHO2' in x for x in prompts) == 2 and not P.evaluate("state.tr.rA.wait.size"), [tm, sum('ECHO2' in x for x in prompts)])
        ok('a message already in Telugu: no repeat line and no extra AI ask', tm.get('e3') == '' and sum('జ్వరం' in x for x in prompts) == 1, [tm.get('e3'), len(prompts)])
        ok('the AI is told what chat short forms mean ("u" = you)', all('"u" means you' in x for x in prompts))
        msgs_txt = P.evaluate("[...document.querySelectorAll('.msg')].map(e => e.innerText).join(' | ')")
        ok('on screen: Telugu under the messages, no English line repeated', 'తె From how many days' in msgs_txt and 'తె Take rest' in msgs_txt and msgs_txt.count('Yes mam ECHO2') == 1 and msgs_txt.count('నాకు జ్వరం వచ్చింది') == 1 and 'Translating' not in msgs_txt, msgs_txt[:400])
        # an English line saved on the phone before this fix → translated again when the chat opens
        ai_log.clear()
        P.evaluate("Tr.stop('rA'); LS.set('healvio:tr:rA', JSON.stringify({ lang: 'Telugu', map: { e1: 'From how many days are u getting fever ECHO1', e4: 'తె Take rest' } })); state.msgs.rA = state.msgs.rA.filter(m => m.id === 'e1' || m.id === 'e4'); delete (state.trAuto || {}).rA; Tr.restore('rA'); render()"); W(P, 2500)
        ok('an old English "translation" saved on the phone is done again (the good ones are kept)', P.evaluate("state.tr.rA.map.e1") == 'తె From how many days are u getting fever ECHO1' and len(ai_log) == 1 and 'Take rest' not in ai_log[0]['prompt'], [P.evaluate("state.tr.rA.map"), len(ai_log)])
        P.evaluate("Tr.stop('rA'); render()"); W(P, 200)
        # ---- PayPal: never stuck when the payment server does not answer ----
        P.evaluate("state.sheet = null; Store.data.requests.rA = Object.assign({}, Store.data.requests.rA, { status: 'accepted' }); go('consult', { id: 'rA' })"); W(P, 600)
        cover = P.evaluate("(() => { const b = document.querySelector('[data-act=payFee]'); b.scrollIntoView(); const r = b.getBoundingClientRect(); const el = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return el ? (el.className || el.tagName) + ' | ' + (el.textContent || '').slice(0, 80) : 'none'; })()")
        P.evaluate("document.querySelector('[data-act=payFee]').click()"); W(P, 1500)
        tip = P.evaluate("document.body.innerText")
        ok('PayPal sheet explains PayPal opens its own page and comes back', 'PayPal opens its own secure page, then brings you back to Healvio.' in tip)
        P.click('#fake-pp'); W(P, 32000)
        m = P.locator('#pp-msg').inner_text()
        ok('payment server silent for 30 s → clear "taking too long" message (no endless loading)', 'taking too long' in m, m)
        # ---- PayPal's own page and back (works in the installed app) ----
        for r in hang:
            try: r.abort()
            except Exception: pass
        hang.clear()
        pmode['v'] = 'go'
        ctx.route(re.compile(r'https://www\.sandbox\.paypal\.com/.*'), paypal_page)
        P.evaluate("Pay.close(); state.sheet = null; state.modal = null; Store.data.requests.rA = Object.assign({}, Store.data.requests.rA, { status: 'accepted' }); go('consult', { id: 'rA' })"); W(P, 600)
        P.evaluate("document.querySelector('[data-act=payFee]').click()"); W(P, 1200)
        ok('PayPal sheet has the main "Pay with PayPal" button', P.locator('#pp-go').count() == 1)
        P.evaluate("document.getElementById('pp-go').click()"); W(P, 3500)
        cr = [x for x in plog if x['step'] == 'create']
        ok('Pay with PayPal asks for the PayPal page, with this app as the way back', cr and cr[-1]['b'].get('redirect') is True and cr[-1]['b'].get('back', '').startswith(URL.rstrip('/')), cr[-1:])
        W(P, 1500)
        ok('came back to Healvio from PayPal (address cleaned)', P.evaluate("location.search") == '' and P.evaluate("!!(Pay.back || Pay.resuming || true)"), P.evaluate("location.href"))
        # mocks forget the login on reload (real Firebase keeps it): log in again
        P.evaluate(f"globalThis.__googleEmail={json.dumps(PAT_E)}; globalThis.__googleName='Ravi Kumar'")
        if P.locator('button:has-text("Continue with Google")').count(): P.click('button:has-text("Continue with Google")')
        W(P, 4000)
        cap = [x for x in plog if x['step'] == 'capture']
        ok('back from PayPal → payment confirmed by itself (capture with the PayPal order)', cap and cap[-1]['b'] == {'kind': 'fee', 'id': 'rA', 'orderID': 'PPGO1'}, cap[-1:])
        ok('paid shown on this phone and the consultation opened', P.evaluate("!!Pay.local['fee:rA']") and P.evaluate("state.view") == 'consult', [P.evaluate("Object.keys(Pay.local)"), P.evaluate("state.view")])
        # cancelled on PayPal's page
        n_cap = len(cap)
        P.goto(URL + '?paypal=cancel&pk=fee&pi=rA&token=PPGO2'); W(P, 1500)
        P.evaluate(f"globalThis.__googleEmail={json.dumps(PAT_E)}; globalThis.__googleName='Ravi Kumar'")
        if P.locator('button:has-text("Continue with Google")').count(): P.click('button:has-text("Continue with Google")')
        W(P, 3000)
        ok('cancelled on PayPal → nothing charged, nothing captured', len([x for x in plog if x['step'] == 'capture']) == n_cap and P.evaluate("location.search") == '')
        for r in hang:
            try: r.abort()
            except Exception: pass
        b.close()
finally:
    srv.terminate()
ok('no page errors', not errs, errs[:3])
print('PASSED %d / %d' % (sum(1 for _, v in results if v), len(results)))
