import fs from 'fs';
const L = {}; let navs = [], msgs = [], deleted = [];
const mk = keys => ({ keys: async () => keys, delete: async k => { deleted.push(k); return true; }, open: async () => ({ addAll: async () => {} }) });
let pass = 0, total = 0; const ok = (n, c, x = '') => { total++; if (c) pass++; console.log((c ? 'PASS ' : 'FAIL ') + n, x === '' ? '' : '| ' + JSON.stringify(x)); };
async function act(keys) {
  navs = []; msgs = []; deleted = [];
  const clients = [{ url: 'https://healvio.web.app/', navigate: async u => navs.push(u), postMessage: m => msgs.push(m) }];
  const self = { addEventListener: (t, f) => (L[t] = f), registration: { scope: 'https://healvio.web.app/' }, clients: { matchAll: async () => clients, claim: async () => {} }, location: { origin: 'https://healvio.web.app' }, skipWaiting() {} };
  new Function('self', 'caches', fs.readFileSync('/home/claude/healvio-app/sw.js', 'utf8'))(self, mk(keys));
  let p; L.activate({ waitUntil: x => (p = x) }); await p;
}
await act(['healvio-v2', 'healvio-v6']);
ok('old installed app (v2) reloads into the new version by itself', navs.length === 1 && deleted.includes('healvio-v2'), { navs, deleted });
await act(['healvio-v5', 'healvio-v6']);
ok('recent app (v5) is told an update is ready (waits if on a call)', navs.length === 0 && msgs[0] && msgs[0].type === 'updated', msgs);
console.log(`PASSED ${pass} / ${total}`);
