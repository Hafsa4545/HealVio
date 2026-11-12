// free fixed-credential relay (ExpressTURN) on /ice and /status
import fs from 'fs';
fs.writeFileSync('./worker7.mjs', fs.readFileSync('../healvio-app/ai-server/worker.js', 'utf8') + '\nexport { fixedTurn };\n');
const W = await import('./worker7.mjs');
const worker = W.default;
const results = []; const ok = (n, c, x) => { results.push(!!c); console.log((c ? 'PASS ' : 'FAIL ') + n + (x !== undefined ? ' | ' + JSON.stringify(x) : '')); };
let cf = 'ok';
globalThis.fetch = async (url) => {
  url = String(url);
  if (url.includes('rtc.live.cloudflare.com')) {
    if (cf === 'down') throw new Error('net');
    if (cf === '401') return new Response('{}', { status: 401 });
    return new Response(JSON.stringify({ iceServers: { urls: ['stun:stun.cloudflare.com:3478', 'turn:turn.cloudflare.com:3478?transport=udp', 'turn:turn.cloudflare.com:53?transport=udp'], username: 'cu', credential: 'cp' } }), { headers: { 'content-type': 'application/json' } });
  }
  throw new Error('unexpected ' + url);
};
const get = async (path, env) => { const r = await worker.fetch(new Request('https://w.test' + path, { headers: { origin: 'https://healvio.web.app' } }), { ALLOWED_ORIGINS: 'https://healvio.web.app', ...env }, { waitUntil() {} }); return r.json(); };
const ET = { TURN_USERNAME: ' 000000002075 ', TURN_PASSWORD: 'secretPW', TURN_SERVER: 'relay1.expressturn.com:3480' };
let j = await get('/ice', {});
ok('no relay set: only STUN, turn false', j.turn === false && j.iceServers.every(x => x.urls.every(u => u.startsWith('stun:'))));
j = await get('/ice', ET);
const e = j.iceServers.find(x => x.username);
ok('ExpressTURN: relay given with username and password', j.turn === true && e && e.username === '000000002075' && e.credential === 'secretPW', e);
ok('ExpressTURN: udp, tcp and tls on the dashboard port', e && e.urls.join(' ') === 'turn:relay1.expressturn.com:3480?transport=udp turn:relay1.expressturn.com:3480?transport=tcp turns:relay1.expressturn.com:443?transport=tcp', e && e.urls);
ok('default server when none typed', W.fixedTurn({ TURN_USERNAME: 'u', TURN_PASSWORD: 'p' })[0].urls[0] === 'turn:relay1.expressturn.com:3478?transport=udp');
ok('pasted "turn:host:port" also works', W.fixedTurn({ TURN_USERNAME: 'u', TURN_PASSWORD: 'p', TURN_SERVER: ' turn:free.expressturn.com:3478 ' })[0].urls[1] === 'turn:free.expressturn.com:3478?transport=tcp');
ok('bad server text ignored safely', W.fixedTurn({ TURN_USERNAME: 'u', TURN_PASSWORD: 'p', TURN_SERVER: 'bad host<script>' }).length === 0);
ok('missing password → no relay', W.fixedTurn({ TURN_USERNAME: 'u' }).length === 0);
const s = await get('/status', ET);
ok('status: turn true with ExpressTURN', s.turn === true);
const s0 = await get('/status', {});
ok('status: turn false with nothing', s0.turn === false);
const both = { ...ET, TURN_KEY_ID: 'k', TURN_KEY_API_TOKEN: 't' };
j = await get('/ice', both);
ok('Cloudflare + ExpressTURN: both relays, port 53 removed', j.turn === true && j.iceServers.length === 2 && !JSON.stringify(j).includes(':53?'));
cf = '401'; j = await get('/ice', both);
ok('Cloudflare key wrong → ExpressTURN still works', j.turn === true && j.iceServers.some(x => x.username === '000000002075'));
cf = 'down'; j = await get('/ice', both);
ok('Cloudflare down → ExpressTURN still works', j.turn === true && j.iceServers.some(x => x.username === '000000002075'));
console.log('\n' + results.filter(Boolean).length + '/' + results.length + ' passed');
