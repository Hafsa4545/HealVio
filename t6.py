import re, subprocess, time
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['python3','-m','http.server','8082'], cwd='/home/claude/healvio-app', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
CFG = 'window.HEALVIO_CONFIG = { firebase: { apiKey: "x", projectId: "healvio-test", appId: "1:2:web:3" }, aiUrl: "" };'
try:
  with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox']); p=b.new_page(viewport={'width':390,'height':844})
    errs=[]; p.on('pageerror', lambda e: errs.append(str(e)))
    p.route(re.compile(r'https://fonts\..*'), lambda r: r.abort())
    p.route('https://www.gstatic.com/**', lambda r: r.fulfill(status=404, body='nope'))
    p.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=CFG))
    p.goto('http://localhost:8082/'); p.wait_for_timeout(1500)
    print('fallback banner:', p.locator('.banner').inner_text() if p.locator('.banner').count() else 'none')
    print('demo buttons:', p.locator('button:has-text("Create account")').count(), '| pageerrors:', errs)
    b.close()
finally: srv.terminate()
