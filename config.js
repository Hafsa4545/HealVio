/*
 * ============================================================
 *  HEALVIO SETTINGS  —  the only file you need to edit
 * ============================================================
 *
 *  Fill in "firebase" below and Healvio is LIVE: Google sign-in,
 *  shared data for every phone, and secure per-person access.
 *  The FREE Firebase plan is enough.
 *  README.md has the step-by-step instructions.
 */
window.HEALVIO_CONFIG = {

  /* Final version: no demo mode. Keep this true. */
  production: true,

  /* 1) FIREBASE — Firebase console → Project settings → Your apps → Web app → Config.
   *    Paste the object here. Example shape:
   *
   *    firebase: {
   *      apiKey: "AIza....",
   *      authDomain: "healvio.firebaseapp.com",
   *      projectId: "healvio",
   *      storageBucket: "healvio.firebasestorage.app",
   *      messagingSenderId: "1234567890",
   *      appId: "1:1234567890:web:abcdef123456"
   *    },
   *
   *    (These values are not secret. Security comes from firebase/firestore.rules.)
   */
  firebase: {
    apiKey: "",
    authDomain: "",
    projectId: "",
    storageBucket: "",
    messagingSenderId: "",
    appId: ""
  },

  /* 2) SMS OTP LOGIN — false = Google sign-in only (FREE).
   *    Set to true only after upgrading Firebase to the Blaze plan and
   *    enabling "Phone" sign-in (each SMS is charged by Google).
   */
  phoneLogin: false,

  /* 3) YOUR WORKER LINK — one link for AI, phone notifications and video-call relay.
   *    Example: "https://healvio-ai.yourname.workers.dev"   (README → Part 3)
   */
  server: "",

  /* 4) PHONE NOTIFICATIONS (free) — Firebase → Project settings → Cloud Messaging →
   *    Web Push certificates → Generate key pair → copy the key and paste it here.
   */
  vapidKey: "",

  /* 5) AI (paid) — change to true after you add Claude credit and ANTHROPIC_API_KEY
   *    to the worker. false = AI listening / summary / translate stay hidden.
   */
  ai: false

  /* ADMINS are set in Firebase, not here: README → "Make yourself admin". */
};
