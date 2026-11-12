(() => {
  const store = new Map(); // path -> data
  const listeners = new Set(); // {kind:'col'|'doc', path, order, lim, next}
  const deepFreeze = o => { if (o && typeof o === 'object') { Object.values(o).forEach(deepFreeze); Object.freeze(o); } return o; };
  const parentOf = p => p.split('/').slice(0, -1).join('/');
  const snapDoc = (path) => { const d = store.get(path); const id = path.split('/').pop(); return { id, exists: !!d, data: () => d ? deepFreeze(JSON.parse(JSON.stringify(d))) : undefined, metadata: { fromCache: false, hasPendingWrites: false } }; };
  const colSnap = (l) => { let docs = [...store.keys()].filter(k => parentOf(k) === l.path).map(snapDoc); if (l.order) docs.sort((a, b) => (a.data()[l.order] > b.data()[l.order] ? 1 : -1)); if (l.lim) docs = docs.slice(0, l.lim); return { docs, size: docs.length, empty: !docs.length, docChanges: () => [], metadata: { fromCache: false, hasPendingWrites: false } }; };
  const fire = () => setTimeout(() => listeners.forEach(l => l.kind === 'col' ? l.next(colSnap(l)) : l.next(snapDoc(l.path))), 5);
  window.__mockStore = store; window.__writes = 0;
  const query = (path, order, lim) => ({
    path,
    where() { return query(path, order, lim); },
    orderBy(f) { return query(path, f, lim); },
    limit(n) { return query(path, order, n); },
    get: async () => colSnap({ path, order, lim }),
    onSnapshot(next, err) { const l = { kind: 'col', path, order, lim, next }; listeners.add(l); setTimeout(() => next(colSnap(l)), 20); return () => listeners.delete(l); },
    doc(id) { if (!id) id = 'x' + Math.random().toString(36).slice(2); return docRef(path + '/' + id); },
    async add(d) { const r = this.doc(); await r.set(d); return r; }
  });
  const check = (p, even) => { const n = p.split('/').length; if ((n % 2 === 0) !== even) throw new TypeError('bad parity ' + p); };
  const docRef = path => { check(path, true); return {
    id: path.split('/').pop(), path,
    get: async () => snapDoc(path),
    async set(d) { if (typeof d !== 'object' || Array.isArray(d)) throw { code: 'invalid_argument' }; const sz = JSON.stringify(d).length; if (sz > 262144) throw { code: 'invalid_argument', message: 'too big ' + sz }; window.__writes++; store.set(path, JSON.parse(JSON.stringify(d))); fire(); },
    async update(d) { if (!store.has(path)) throw { code: 'invalid_argument' }; store.set(path, { ...store.get(path), ...d }); fire(); },
    async delete() { store.delete(path); fire(); },
    onSnapshot(next) { const l = { kind: 'doc', path, next }; listeners.add(l); setTimeout(() => next(snapDoc(path)), 20); return () => listeners.delete(l); },
    collection(sub) { const p = path + '/' + sub; check(p, false); return query(p); }
  }; };
  const db = { doc: p => docRef(p), collection: p => { check(p, false); return query(p); } };
  const sample = async (input, opts) => ({ text: 'ok', truncated: false });
  window.__ai = [];
  sample.json = async (input) => {
    window.__ai.push(input.slice(0, 80));
    await new Promise(r => setTimeout(r, 200));
    if (input.startsWith('Translate')) { const m = input.match(/JSON array of (\d+) strings/); return Array.from({ length: +m[1] }, (_, i) => 'అనువాదం ' + i); }
    if (input.includes('silent AI listener')) return { doubts: [{ point: 'How long to take paracetamol was unclear', suggested_question: 'Should I stop paracetamol once the fever is gone?' }] };
    if (input.includes('Summarize this completed consultation')) return { summary: 'You have a viral fever. Take the medicines as prescribed and rest.', key_points: ['Paracetamol 650 mg three times a day for 3 days'], doubts_clarified: [{ question: 'Is it serious?', answer: 'No, it is a common viral fever.' }], instant_relief: ['Warm fluids', 'Cold sponging above 101F'], hospital_visit: 'Visit if symptoms continue after 3 days', follow_up: 'After 5 days', open_questions: [] };
    return {};
  };
  sample.limits = async () => ({ maxPromptBytes: 262144 });
  window.__dl = [];
  const downloads = { save: async ({ filename, data }) => { window.__dl.push([filename, data.length]); return { status: 'saved' }; } };
  const user = { isOwner: async () => true, canEdit: async () => true, id: async () => 'u_test', can: async () => true };
  window.claude = { use: async name => { await new Promise(r => setTimeout(r, 30)); return { db, sample, downloads, user }[name] || null; } };
})();
