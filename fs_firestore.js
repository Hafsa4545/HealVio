const store = (globalThis.__fsStore ||= new Map());
const listeners = (globalThis.__fsL ||= new Set());
globalThis.__fsWrites = globalThis.__fsWrites || 0;
export function getFirestore(app) { return { app }; }
export function doc(db, path) {
  if (db && db.__col) { const id = 'auto' + Math.random().toString(36).slice(2); return { id, path: db.path + '/' + id }; }
  const parts = path.split('/'); if (parts.length % 2) throw new Error('bad doc path ' + path);
  return { id: parts[parts.length - 1], path };
}
export function collection(db, path) { if (path.split('/').length % 2 === 0) throw new Error('bad col path ' + path); return { __col: true, path }; }
export function query(base, ...cons) { return { ...base, cons }; }
export const where = (f, op, v) => ({ t: 'where', f, op, v });
export const orderBy = (f, d) => ({ t: 'orderBy', f, d });
export const limit = n => ({ t: 'limit', n });
const copy = o => JSON.parse(JSON.stringify(o));
function dsnap(path) { const d = store.get(path); return { id: path.split('/').pop(), exists: () => !!d, data: () => d ? Object.freeze(copy(d)) : undefined, metadata: { fromCache: false, hasPendingWrites: false } }; }
function qsnap(q) {
  let docs = [...store.keys()].filter(k => k.split('/').slice(0, -1).join('/') === q.path).map(dsnap);
  for (const c of q.cons || []) { if (c.t === 'orderBy') docs.sort((a, b) => a.data()[c.f] > b.data()[c.f] ? 1 : -1); if (c.t === 'limit') docs = docs.slice(0, c.n); }
  return { docs, size: docs.length, metadata: { fromCache: false, hasPendingWrites: false } };
}
const fire = () => setTimeout(() => listeners.forEach(l => l()), 5);
function noUndef(o) { if (o === undefined) throw { code: 'invalid-argument', message: 'undefined value' }; if (o && typeof o === 'object') Object.values(o).forEach(noUndef); }
export async function setDoc(ref, d) { noUndef(d); if (JSON.stringify(d).length > 1048000) throw { code: 'invalid-argument', message: 'too big' }; globalThis.__fsWrites++; store.set(ref.path, copy(d)); fire(); }
export async function getDoc(ref) { return dsnap(ref.path); }
export async function getDocs(q) { return qsnap(q); }
export async function updateDoc(ref, d) { store.set(ref.path, { ...store.get(ref.path), ...d }); fire(); }
export async function deleteDoc(ref) { store.delete(ref.path); fire(); }
export function onSnapshot(target, next, err) { const l = target.__col ? () => next(qsnap(target)) : () => next(dsnap(target.path)); listeners.add(l); setTimeout(l, 10); return () => listeners.delete(l); }
