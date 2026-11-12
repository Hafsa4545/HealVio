// In-memory Firestore that enforces the same access policy as firebase/firestore.rules
const store = (globalThis.__fsStore ||= new Map());
const listeners = (globalThis.__fsL ||= new Set());
const denied = (globalThis.__denied ||= []);
const uid = () => globalThis.__authUid || null;
const signed = () => !!uid();
const isAdmin = () => signed() && store.has('admins/' + uid());
const D = p => store.get(p);
const parent = p => p.split('/').slice(0, -1).join('/');
const copy = o => JSON.parse(JSON.stringify(o));
const changedKeys = (n, o) => { const ks = new Set([...Object.keys(n || {}), ...Object.keys(o || {})]); return [...ks].filter(k => JSON.stringify((n || {})[k]) !== JSON.stringify((o || {})[k])); };
const only = (arr, allowed) => arr.every(k => allowed.includes(k));
const req = rid => D('requests/' + rid) || {};
function canList(col, wh) {
  const w = {}; (wh || []).forEach(c => { if (c.op === '==') w[c.f] = c.v; });
  const seg = col.split('/');
  if (seg.length === 3 && seg[0] === 'calls' && seg[2] === 'ice') { const cl = D('calls/' + seg[1]) || {}; return signed() && (cl.from === uid() || cl.to === uid()); }
  if (seg.length === 3 && seg[0] === 'requests' && seg[2] === 'messages') { const r = req(seg[1]); return signed() && (r.patientId === uid() || r.doctorId === uid() || isAdmin()); }
  if (['public', 'reviews', 'slots'].includes(col)) return signed();
  if (col === 'accounts') return isAdmin();
  if (col === 'requests' || col === 'prescriptions') return signed() && (isAdmin() || w.patientId === uid() || w.doctorId === uid());
  if (col === 'orders') return signed() && (isAdmin() || w.patientId === uid() || w.storeId === uid());
  if (col === 'notifications') return signed() && (w.to === uid() || (w.to === 'admin' && isAdmin()));
  if (col === 'calls') return signed() && (w.to === uid() || w.from === uid() || isAdmin());
  if (col === 'reminders') return signed() && w.uid === uid();
  if (col === 'complaints') return signed() && (isAdmin() || w.by === uid());
  return false;
}
function canGet(path) {
  const [col, id] = path.split('/'); const d = D(path);
  if (!signed()) return false;
  if (col === 'admins') return id === uid();
  if (col === 'accounts') return id === uid() || isAdmin();
  if (col === 'files') return !!d && (d.public === true || d.owner === uid() || isAdmin());
  if (['public', 'reviews', 'slots'].includes(col)) return true;
  if (col === 'pushTokens') return id === uid();
  if (!d) return isAdmin() || col === 'reminders';
  if (col === 'requests' || col === 'prescriptions') return d.patientId === uid() || d.doctorId === uid() || isAdmin();
  if (col === 'orders') return d.patientId === uid() || d.storeId === uid() || isAdmin();
  if (col === 'calls') return d.from === uid() || d.to === uid() || isAdmin();
  if (col === 'pushTokens') return id === uid();
  if (col === 'reminders') return d.uid === uid();
  if (col === 'system') return isAdmin();
  if (col === 'complaints') return d.by === uid() || isAdmin();
  return false;
}
function canWrite(path, n, o, del) {
  if (!signed()) return false;
  const seg = path.split('/'), col = seg[0], id = seg[1], me = uid(), admin = isAdmin();
  const acc = D('accounts/' + me);
  const approved = !!acc && acc.status === 'approved';
  if (seg.length === 4 && seg[0] === 'calls' && seg[2] === 'ice') { const cl = D('calls/' + id) || {}; return !del && !o && n.from === me && (cl.from === me || cl.to === me) && only(Object.keys(n), ['from', 'c', 'rev', 'at']); }
  if (seg.length === 4 && seg[2] === 'messages') { const r = req(id); return !del && !o && (r.patientId === me || r.doctorId === me) && (n.from === me || n.from === 'system'); }
  if (col === 'admins') return false;
  if (col === 'complaints') { if (del) return admin; if (!o) return n.by === me && n.id === id && n.status === 'open' && typeof n.text === 'string' && n.text.length <= 2000 && !('reply' in n) && !('resolvedAt' in n); return admin && only(changedKeys(n, o), ['status', 'reply', 'resolvedAt', 'updatedAt']); }
  if (col === 'accounts') {
    if (del) return id === me || admin;
    if (admin) return true;
    if (id !== me || n.id !== me) return false;
    if (!o) return ((n.role === 'patient' && n.status === 'active') || (['doctor', 'store'].includes(n.role) && n.status === 'draft')) && !n.demo;
    return n.role === o.role && !!n.demo === !!o.demo && (n.status === o.status || (['draft', 'rejected'].includes(o.status) && n.status === 'pending'));
  }
  if (col === 'public') { if (del) return id === me || admin; return admin || (id === me && approved && n.id === me && n.status === 'approved' && n.role === acc.role); }
  if (col === 'requests') {
    if (del) return admin;
    if (!o) return n.patientId === me && n.status === 'requested' && !('paid' in n) && !('refund' in n) && store.has('public/' + n.doctorId);
    if (admin) return true;
    const ch = changedKeys(n, o);
    if (o.doctorId === me) return n.doctorId === o.doctorId && n.patientId === o.patientId && !ch.some(k => ['rating', 'review', 'ratedAt', 'paid', 'refund'].includes(k)) && !(n.status === 'rejected' && o.status !== 'rejected' && o.paid != null && o.refund == null);
    if (o.patientId === me) return only(ch, ['status', 'closedAt', 'updatedAt', 'rating', 'review', 'ratedAt', 'aiSummary', 'rateSkipped']) && (n.status === o.status || (n.status === 'cancelled' && ['requested', 'waiting', 'accepted'].includes(o.status) && o.paid == null)) && (!ch.includes('rating') || o.status === 'completed');
    return false;
  }
  if (col === 'prescriptions') {
    if (del) return admin;
    if (!o) { const r = req(n.requestId); return approved && n.doctorId === me && r.doctorId === me && r.patientId === n.patientId; }
    return o.doctorId === me && n.doctorId === me && n.patientId === o.patientId;
  }
  if (col === 'orders') {
    if (del) return admin;
    if (!o) return n.patientId === me && n.status === 'sent' && !['paid', 'refund', 'total', 'deliveryFee', 'rider', 'riderName', 'riderPhone', 'outAt', 'deliveredAt', 'collectedAt'].some(k => k in n)
      && ((n.rxId == null && typeof n.paperRx === 'string' && n.paperRx.length > 100 && n.paperRx.length < 1000000 && /^data:image\/(jpeg|png|webp);base64,/.test(n.paperRx)) || (D('prescriptions/' + n.rxId) || {}).patientId === me);
    if (admin) return true;
    if (o.storeId === me) return only(changedKeys(n, o), ['status', 'items', 'note', 'total', 'deliveryFee', 'respondedAt', 'updatedAt', 'rider', 'riderName', 'riderPhone', 'outAt', 'nearAt', 'deliveredAt', 'collectedAt', 'closedAt']) && (!changedKeys(n, o).some(k => k === 'total' || k === 'deliveryFee') || o.paid == null) && !(['unavailable', 'cancelled'].includes(n.status) && o.paid != null && o.refund == null);
    if (o.patientId === me) return ['sent', 'ready', 'partial'].includes(o.status) && n.status === 'cancelled' && only(changedKeys(n, o), ['status', 'closedAt', 'updatedAt']) && o.paid == null;
    return false;
  }
  if (col === 'notifications') {
    if (del) return admin;
    if (!o) return typeof n.text === 'string' && n.text.length <= 600 && (n.from === undefined || n.from === me);
    return (o.to === me || (o.to === 'admin' && admin)) && only(changedKeys(n, o), ['read', 'updatedAt']);
  }
  if (col === 'reviews') { if (del) return admin; if (o) return o.doctorId === me && only(changedKeys(n, o), ['reply', 'replyAt', 'updatedAt']) && typeof n.reply === 'string' && n.reply.length <= 600; const r = req(id); return n.id === id && n.patientId === me && r.patientId === me && r.doctorId === n.doctorId && r.status === 'completed' && Number.isInteger(n.rating) && n.rating >= 1 && n.rating <= 5; }
  if (col === 'slots') { if (del) return admin; if (id === me || admin) return true; return o ? only(changedKeys(n, o), ['emergency', 'updatedAt']) : only(Object.keys(n), ['id', 'emergency', 'updatedAt']); }
  if (col === 'calls') {
    if (del) return admin;
    if (!o) { const r = req(n.rid); return n.id === id && n.from === me && n.status === 'ringing' && ['video', 'audio'].includes(n.kind) && only(Object.keys(n), ['id', 'rid', 'from', 'to', 'fromName', 'kind', 'status', 'offer', 'rev', 'createdAt', 'updatedAt']) && r.status === 'live' && ((r.doctorId === me && r.patientId === n.to) || (r.patientId === me && r.doctorId === n.to)); }
    return (o.from === me || o.to === me) && only(changedKeys(n, o), ['status', 'answer', 'acceptedAt', 'endedAt', 'endedBy', 'updatedAt', 'offer', 'rev', 'arev', 'restartAsk']) && ['ringing', 'accepted', 'declined', 'busy', 'cancelled', 'missed', 'ended'].includes(n.status);
  }
  if (col === 'pushTokens') return id === me;
  if (col === 'pushLog') return false;
  if (col === 'system') return false;
  if (col === 'reminders') { if (del) return !!o && o.uid === me; return n.uid === me && (!o || o.uid === me); }
  if (col === 'files') { if (del) return !!o && (o.owner === me || admin); if (o) return false; return n.owner === me; }
  return false;
}
const deny = (what, path) => { denied.push(what + ' ' + path + ' as ' + uid()); return { code: 'permission-denied', message: 'Missing or insufficient permissions (' + what + ' ' + path + ')' }; };
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
function dsnap(path) { const d = D(path); return { id: path.split('/').pop(), exists: () => !!d, data: () => d ? Object.freeze(copy(d)) : undefined, metadata: { fromCache: false, hasPendingWrites: false } }; }
function qsnap(q) {
  const wh = (q.cons || []).filter(c => c.t === 'where').map(c => ({ f: c.f, op: c.op, v: c.v }));
  let docs = [...store.keys()].filter(k => parent(k) === q.path).filter(k => wh.every(c => c.op === '==' ? D(k)[c.f] === c.v : true)).map(dsnap);
  for (const c of q.cons || []) { if (c.t === 'orderBy') docs.sort((a, b) => a.data()[c.f] > b.data()[c.f] ? 1 : -1); if (c.t === 'limit') docs = docs.slice(0, c.n); }
  return { docs, size: docs.length, metadata: { fromCache: false, hasPendingWrites: false } };
}
const fire = () => setTimeout(() => listeners.forEach(l => l()), 5);
const bc = new BroadcastChannel('fs-sync');
const bcast = (path) => { try { bc.postMessage({ t: 'w', path, d: store.has(path) ? store.get(path) : null }); } catch (e) {} };
bc.onmessage = ev => { const m = ev.data; if (m.t === 'w') { if (m.d === null) store.delete(m.path); else store.set(m.path, m.d); fire(); }
  else if (m.t === 'hello') bc.postMessage({ t: 'dump', entries: [...store.entries()] });
  else if (m.t === 'dump') { m.entries.forEach(([k, v]) => { if (!store.has(k)) store.set(k, v); }); fire(); } };
bc.postMessage({ t: 'hello' });
globalThis.__fsFire = fire;
function noUndef(o) { if (o === undefined) throw { code: 'invalid-argument', message: 'undefined value' }; if (o && typeof o === 'object') Object.values(o).forEach(noUndef); }
export async function setDoc(ref, d) { noUndef(d); if (!canWrite(ref.path, d, D(ref.path), false)) throw deny('write', ref.path); store.set(ref.path, copy(d)); bcast(ref.path); fire(); }
export async function getDoc(ref) { if (!canGet(ref.path)) throw deny('get', ref.path); return dsnap(ref.path); }
export async function getDocs(q) { if (!canList(q.path, (q.cons || []).filter(c => c.t === 'where'))) throw deny('list', q.path); return qsnap(q); }
export async function updateDoc(ref, d) { const n = { ...D(ref.path), ...d }; if (!canWrite(ref.path, n, D(ref.path), false)) throw deny('update', ref.path); store.set(ref.path, n); bcast(ref.path); fire(); }
export async function deleteDoc(ref) { if (!canWrite(ref.path, null, D(ref.path), true)) throw deny('delete', ref.path); store.delete(ref.path); bcast(ref.path); fire(); }
export function onSnapshot(target, next, err) {
  if (target.__col) { if (!canList(target.path, (target.cons || []).filter(c => c.t === 'where'))) { const e = deny('listen', target.path + JSON.stringify((target.cons || []).map(c => [c.f, c.v]))); setTimeout(() => err && err(e), 5); return () => {}; } }
  else if (!canGet(target.path)) { const e = deny('listen', target.path); setTimeout(() => err && err(e), 5); return () => {}; }
  const l = target.__col ? () => next(qsnap(target)) : () => next(dsnap(target.path));
  listeners.add(l); setTimeout(l, 10); return () => listeners.delete(l);
}

// --- offline cache API (like Firebase 10+) ---
export function persistentMultipleTabManager() { return { kind: 'multi-tab' }; }
export function persistentLocalCache(o) { return { kind: 'persistent', tabManager: o && o.tabManager }; }
export function initializeFirestore(app, opts) { (globalThis.__fsInit = globalThis.__fsInit || []).push(JSON.stringify(opts)); return getFirestore(app); }
export async function terminate(db) { (globalThis.__fsLog = globalThis.__fsLog || []).push('terminate'); try { localStorage.setItem('__fsTerm', String((+localStorage.getItem('__fsTerm') || 0) + 1)); } catch (e) {} }
export async function clearIndexedDbPersistence(db) { (globalThis.__fsLog = globalThis.__fsLog || []).push('clear'); try { localStorage.setItem('__fsClear', String((+localStorage.getItem('__fsClear') || 0) + 1)); } catch (e) {} }
