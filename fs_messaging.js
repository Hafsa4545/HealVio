export async function isSupported() { return true; }
export function getMessaging(app) { if (!app) throw new Error('no app'); return { app }; }
export async function getToken(m, opts) {
  (globalThis.__gt = globalThis.__gt || []).push(opts && opts.vapidKey ? 'key' : 'default');
  const mode = globalThis.__pushMode || '';
  if (opts && opts.vapidKey && (mode === 'keyfail' || mode === 'allfail')) { const e = new Error('Registration failed - push service error'); e.name = 'AbortError'; e.code = 20; throw e; }
  if (mode === 'allfail') { const e = new Error('Registration failed - push service error'); e.name = 'AbortError'; e.code = 20; throw e; }
  if (opts && opts.vapidKey && opts.vapidKey !== 'VAPID-KEY' && opts.vapidKey !== globalThis.__realKey) throw new Error('bad vapid');
  if (!opts.serviceWorkerRegistration || !opts.serviceWorkerRegistration.pushManager) throw new Error('no sw registration');
  if (Notification.permission !== 'granted') throw new Error('permission');
  return 'fcm-' + (globalThis.__devName || 'dev') + (globalThis.__tokGen ? '-' + globalThis.__tokGen : '');
}
export async function deleteToken() { globalThis.__tokGen = (globalThis.__tokGen || 0) + 1; return true; }
