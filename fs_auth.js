let current = null; const listeners = new Set();
const setUser = u => { if (u) u.getIdToken = async () => 'idtoken-' + u.uid; current = u; globalThis.__authUid = u ? u.uid : null; listeners.forEach(cb => cb(u)); };
export function getAuth(app) { return { get currentUser() { return current; }, useDeviceLanguage() {} }; }
export function onAuthStateChanged(auth, cb) { listeners.add(cb); setTimeout(() => cb(current), 15); return () => listeners.delete(cb); }
export class RecaptchaVerifier { constructor(auth, id, params) { if (!document.getElementById(id)) throw new Error('missing recaptcha container ' + id); this.id = id; } clear() {} }
export async function signInWithPhoneNumber(auth, phone, verifier) {
  if (!(verifier instanceof RecaptchaVerifier)) throw { code: 'auth/argument-error' };
  if (!/^\+\d{8,15}$/.test(phone)) throw { code: 'auth/invalid-phone-number' };
  globalThis.__lastSms = phone;
  return { confirm: async code => { if (code !== '123456') throw { code: 'auth/invalid-verification-code' }; const u = { uid: 'u' + phone.replace(/\D/g, ''), phoneNumber: phone, email: null, displayName: null }; setUser(u); return { user: u }; } };
}
export class GoogleAuthProvider {}
export async function signInWithPopup(auth, p) { const e = globalThis.__googleEmail || 'g.user@example.com'; const u = { uid: 'g' + e.replace(/\W/g, ''), phoneNumber: null, email: e, displayName: globalThis.__googleName || 'Google User' }; setUser(u); return { user: u }; }
export async function signInWithRedirect() {}
export async function getRedirectResult() { return null; }
export async function signOut() { setUser(null); }
export async function deleteUser() { globalThis.__deletedUsers = (globalThis.__deletedUsers || 0) + 1; setUser(null); }
