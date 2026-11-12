import worker from './worker.mjs';
let sent;
const env = { ANTHROPIC_API_KEY: 'sk-test', ALLOWED_ORIGINS: 'https://healvio.web.app' };
const get = (path, origin = 'https://healvio.web.app') => new Request('https://w.dev' + path, { method: 'GET', headers: { Origin: origin } });
// 1. no TURN keys → STUN only
let r = await worker.fetch(get('/ice'), env); console.log('ice no-turn:', r.status, await r.text(), r.headers.get('Access-Control-Allow-Origin'));
// 2. TURN keys → calls Cloudflare, drops port 53
globalThis.fetch = async (url, init) => { sent = { url, init }; return new Response(JSON.stringify({ iceServers: [{ urls: ['stun:stun.cloudflare.com:3478', 'stun:stun.cloudflare.com:53', 'turn:turn.cloudflare.com:3478?transport=udp', 'turn:turn.cloudflare.com:53?transport=udp', 'turns:turn.cloudflare.com:443?transport=tcp'], username: 'u', credential: 'p' }] }), { status: 201 }); };
r = await worker.fetch(get('/ice/'), { ...env, TURN_KEY_ID: 'kid', TURN_KEY_API_TOKEN: 'tok' });
const j = await r.json();
console.log('ice turn:', r.status, JSON.stringify(j), '| url:', sent.url, '| auth:', sent.init.headers.Authorization, '| body:', sent.init.body);
// 3. old object-shaped response also works
globalThis.fetch = async () => new Response(JSON.stringify({ iceServers: { urls: ['turn:turn.cloudflare.com:3478?transport=udp'], username: 'a', credential: 'b' } }), { status: 201 });
r = await worker.fetch(get('/ice'), { ...env, TURN_KEY_ID: 'k', TURN_KEY_API_TOKEN: 't' }); console.log('object shape:', await r.text());
// 4. Cloudflare error → falls back to STUN
globalThis.fetch = async () => new Response('nope', { status: 401 });
r = await worker.fetch(get('/ice'), { ...env, TURN_KEY_ID: 'k', TURN_KEY_API_TOKEN: 't' }); console.log('cf error:', await r.text());
// 5. other site blocked
r = await worker.fetch(get('/ice', 'https://evil.example'), env); console.log('blocked:', r.status);
// 6. AI still works on POST /
globalThis.fetch = async (url, init) => { sent = { url, body: JSON.parse(init.body) }; return new Response(JSON.stringify({ content: [{ type: 'text', text: 'ok' }], stop_reason: 'end_turn' }), { status: 200 }); };
r = await worker.fetch(new Request('https://w.dev/', { method: 'POST', headers: { Origin: 'https://healvio.web.app', 'content-type': 'application/json' }, body: JSON.stringify({ prompt: 'hi' }) }), { ...env, MODEL: 'claude-haiku-5-5' });
console.log('ai:', r.status, await r.text(), sent.body.model);
r = await worker.fetch(get('/'), env); console.log('GET / :', r.status);
