export async function isSupported() { return true; }
export function getMessaging(app) { return { app }; }
export async function getToken() { const e = new Error('Messaging: A problem occurred while subscribing the user to FCM: FCM Registration API has not been used in project 315550277140 before or it is disabled. (messaging/token-subscribe-failed).'); e.code = 'messaging/token-subscribe-failed'; throw e; }
