# Healvio

**AI telemedicine for India, in 12 languages, with PayPal at every step of care.**

- **Live app:** https://healvio.web.app (installable on Android and iPhone)
- **Built for:** PayPal AI Hackathon 2026, "Build What's Next with PayPal and AI"
- **Demo video and full story:** see our Devpost page

Healvio is one installable web app with four roles: **Patient**, **Doctor**, **Medical store** and **Admin**. It carries a patient from "I feel unwell" to "my medicines are at my door": find the right doctor with AI, book, pay with PayPal, consult by video and chat in their own language, get an e-prescription and an AI summary, then order medicines and track the delivery live.

## How Healvio uses PayPal (Sandbox)

| What | How |
|---|---|
| Consultation fees | The patient pays the doctor's fee with the PayPal JavaScript SDK buttons. The order is **created and captured on our server** with the **Orders API v2**, which checks the price itself, so the amount can't be changed in the browser. The doctor can start the consultation only after the server confirms "Fee paid". |
| Medicine orders and delivery fees | The pharmacy confirms the medicines and the delivery fee; the patient pays the total with PayPal (or cash at the door / counter). |
| Refunds | If a doctor or store cancels something that was paid, the server refunds the capture through the **Payments API v2** (`/v2/payments/captures/{id}/refund`), and the patient is told. |
| Payment reminders | A scheduled job reminds patients to pay 1 hour and 10 minutes before their slot. |
| Installed apps | Inside an installed mobile web app, where pop-ups are blocked, checkout switches to a redirect flow and comes back to the right screen. |

Code: `ai-server/worker.js` (`/pay/create`, `/pay/capture`, `/pay/refund`) and the `Pay` part of `index.html`. The PayPal secret is a Cloudflare worker secret and is never in this repository.

## How Healvio uses AI

| Feature | Model |
|---|---|
| AI Doctor Finder: symptoms in your own words → the right kind of doctor, system of medicine and urgency, with an emergency warning | Llama 3.3 70B |
| Live chat translation between doctor and patient (12 languages) | Llama 3.3 70B / Llama 3.1 8B |
| AI call notes: each phone turns its own speech into text during video and voice calls | Whisper large-v3-turbo |
| Consultation summary with SOAP notes, checked against the source, in the patient's language and read aloud | Llama 3.3 70B |
| "AI: my doubts": questions the patient may want to ask before the visit ends | Llama 3.3 70B |
| Paper prescription reader: a photo of a handwritten prescription becomes a medicine list to order | Llama 4 Scout / Llama 3.2 11B Vision |
| The whole patient app in 12 languages: built-in word lists and alert patterns (`i18n/`), AI only for names and free text | Llama 3.3 70B |

All AI runs on our server on **Cloudflare Workers AI** (free tier), only for signed-in users. Safety rules: AI never invents medical facts, always says it is not a diagnosis and never replaces the doctor.

## Tech stack

Firebase (Google sign-in, Firestore with security rules, Hosting, Cloud Messaging) · Cloudflare Workers (+ Workers AI, Cron) · PayPal Sandbox · WebRTC video and voice calls · Leaflet + OpenStreetMap · a plain JavaScript installable web app with a service worker.

## What is in this repository

| Path | What it is |
|---|---|
| `index.html` | The whole app (patient, doctor, store and admin screens) |
| `backend.js` | Connection to Firebase (sign-in and database) |
| `sw.js` | Service worker: opens offline, phone pop-ups (in the patient's language) |
| `config.js` | Your settings (fill in, see below). No secrets go here |
| `firebase/firestore.rules` | Database security rules |
| `ai-server/worker.js` | The server: PayPal, AI, phone notifications, reminders, call relay |
| `i18n/` | The app's words and alert patterns in 11 Indian languages |
| `privacy.html`, `terms.html` | Privacy policy and terms |
| `tests/` | Automated tests (see `tests/README.md`) |

## Run it yourself

Everything runs on free plans. Follow the **Setup and launch guide** below: Firebase (sign-in, database, hosting), then the Cloudflare worker (Part 3) with these secrets: `FIREBASE_SERVICE_ACCOUNT`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, plus the Workers AI binding `AI`. Never commit keys or service-account files.

## Tests

886 automated checks in 40 test suites: browser tests with two phones (doctor and patient) using Playwright, plus Node tests for the worker (PayPal, push alerts, AI, reminders, consultation timer) and the service worker.

## License

MIT, see `LICENSE`.

---

# Setup and launch guide

## ⭐ START HERE: 8 steps, all free

1. **Firebase → Security → Authentication → Get started → Sign-in method → Google → Enable → your Gmail → Save.**
2. **Firebase → Databases and storage → Firestore Database → Create database** → Standard → **asia-south1 (Mumbai)** → Production mode → Create.
3. **Firestore → Rules:** open `firebase/firestore.rules` in Notepad → **Ctrl+A**, **Ctrl+C** → paste into Firebase → **Publish**.
4. **Project Overview → + Add app → `</>` Web** → name `healvio-web` → Register. Copy the lines from `apiKey` to `appId` into `config.js` inside `firebase: { ... }` → **Ctrl+S**.
5. In the `healvio` folder, click the address bar → type `cmd` → Enter → type `py -m http.server 8080` → open **http://localhost:8080** in Chrome. Log in with Google and choose **Patient**.
6. **Make yourself admin:** app **Profile → Copy** your user ID → Firebase **Firestore → Data → + Start collection** `admins` → Document ID = your ID → field `name` = your name → Save → reload the app.
7. **Put it online:** install Node.js LTS from nodejs.org. Then, in a new `cmd` window in the folder:
   ```
   npm install -g firebase-tools
   firebase login
   firebase deploy --project healvio
   ```
8. **Done:** your app is live at **https://healvio.web.app**. On Android, open it in Chrome → ⋮ → **Install app**. Share the link with doctors and patients.

Every section below explains these steps in more detail.

---

Healvio is a telemedicine app with four sides: **Patient**, **Doctor**, **Medical store** and **Admin**. This folder is the complete app, ready to launch:

- **Real login:** Google sign-in (free). SMS OTP can be switched on later (paid).
- **Secure data:** patients see only their own records, doctors only their own patients, stores only prescriptions sent to them. Only admins approve or terminate doctors.
- **Play Store requirements included:** in-app account deletion, a privacy policy page with a deletion section, a medical disclaimer, and a test login for Google's reviewers.

**Launching for free:** Google login, the database, hosting, and installing on Android from your website link all work on Firebase's free **Spark** plan, so you don't need a card. Only these cost money, and they're all optional:
- **SMS OTP:** needs the Blaze plan, charged per SMS.
- **AI features:** Claude API, charged per use.
- **Google Play Store:** a one-time fee.

**How you'll launch:**

| Route | Who can use it | What you need | Time |
|---|---|---|---|
| **A. Website app** (do this first) | Anyone on Android or iPhone: open your link → **Install app** | Firebase (Parts 1–4) | About 1 day |
| **B. Google Play Store** | Anyone, from the Play Store | Route A + an **Organization** Play developer account (business registration + D-U-N-S number) | A few weeks |

Google Play requires health and medical apps to be published from an Organization account, not a personal one (see Part 6).

---

## What's in the folder

| File / folder | What it is |
|---|---|
| `index.html` | The whole app |
| `i18n/` | The app's words in 11 Indian languages (patients choose their language) |
| `config.js` | **Your settings**: Firebase keys and AI link. The only file you must edit. |
| `backend.js` | Connects the app to Firebase and your AI server |
| `firebase/firestore.rules` | **Security rules**: who can read and change what |
| `firebase.json` | Settings for publishing with Firebase Hosting |
| `privacy.html` | Privacy policy and account-deletion page (template: fill in your details) |
| `manifest.webmanifest`, `sw.js`, `icons/` | Make it installable on phones |
| `ai-server/worker.js` | Small server that keeps your Claude API key secret |

---

## Part 1 — Open it on your laptop

1. Install Python from [python.org](https://www.python.org/downloads/). On Windows, tick **"Add Python to PATH"**.
2. Open a terminal **inside the healvio folder**:
   - **Windows:** click the folder's address bar, type `cmd`, press Enter.
   - **Mac:** right-click the folder → **New Terminal at Folder**.
3. Run `py -m http.server 8080` (or `python -m http.server 8080`).
4. Open **http://localhost:8080** in Chrome.

Until `config.js` has your Firebase settings (Part 2), the app shows a **"Connect Healvio to Firebase"** screen.

---

## Part 2 — Set up Firebase (real login and shared data)

### 2.1 Create the project (free)
1. Go to [console.firebase.google.com](https://console.firebase.google.com) → **Create a project** → name it `healvio`. Turn Google Analytics off.
2. Stay on the free **Spark** plan. **Don't click Upgrade.**

### 2.2 Turn on Google login (free)
1. In the left menu, open **Security** (older consoles call it **Build**) → **Authentication** → **Get started**.
2. Open the **Sign-in method** tab → **Google** → turn on **Enable**.
3. Choose your Gmail as the **support email** and click **Save**.

**Later, to add SMS OTP (paid):** click **Upgrade** to the Blaze plan, then enable **Phone** in Sign-in method. In `config.js`, set `phoneLogin: true`. Under **Phone numbers for testing**, add `+91 9000000001` with code `123456`; test numbers never send a real SMS.

### 2.3 Create the database
1. **Build → Firestore Database → Create database**.
2. Location: **asia-south1 (Mumbai)**. Choose **Production mode**.
3. Open the **Rules** tab. Delete everything, paste the whole of `firebase/firestore.rules`, and click **Publish**.

### 2.4 Connect the app
1. Click the gear icon → **Project settings** → **Your apps** → the **Web** icon (`</>`). Register an app called `healvio-web`.
2. Copy the `firebaseConfig` values into `config.js`:
   ```js
   firebase: {
     apiKey: "AIza...",
     authDomain: "healvio-xxxx.firebaseapp.com",
     projectId: "healvio-xxxx",
     storageBucket: "healvio-xxxx.firebasestorage.app",
     messagingSenderId: "123...",
     appId: "1:123...:web:..."
   },
   ```
3. Reload **http://localhost:8080**. You'll now see **Continue with phone number** and **Continue with Google**.

### 2.5 Make yourself admin
1. In the app, tap **Continue with Google**, log in with your Gmail, and complete your profile as a **Patient**.
2. Go to **Profile → Your user ID → Copy**.
3. In Firebase: **Firestore Database → Data → + Start collection**.
   - Collection ID: `admins`
   - Document ID: paste your user ID
   - Add one field: `name` (string) = your name → **Save**.
4. Back in the app: **Profile → Open admin console**.

To add another admin later, add another document to `admins` with that person's user ID. Only people listed there can approve doctors, and the security rules enforce this.

### 2.6 Test every side
- **Doctor:** log out, log in with a *different* Gmail account (create a free one, or ask a friend), choose **Doctor**, upload documents and sign. Then log in with your own Gmail (admin) and **Approve**.
- **Store:** same steps, choosing **Medical store**.
- **Patient:** request a consult, chat, get a prescription, rate, and send it to the store.

---

## Part 3 — Your worker: AI, phone notifications, stronger calls

Video and voice calls already work without this part. One small free server (a Cloudflare Worker) adds:
- **Phone notifications** (free): alerts and incoming calls reach the phone even when Healvio is closed.
- **AI listening, summary, translate, doubt check** (paid per use, about ₹0.10 a consult with Haiku).
- **Call relay** (free, optional): calls connect on strict mobile networks.

### 3.1 Get two things from Firebase (free)
1. Firebase → ⚙️ **Project settings → Cloud Messaging** → **Web Push certificates** → **Generate key pair**. Copy the key (starts with `B…`).
2. Firebase → ⚙️ **Project settings → Service accounts** → **Generate new private key** → **Generate key**. A `.json` file downloads. Keep it secret.

### 3.2 Create the worker (free)
1. [dash.cloudflare.com](https://dash.cloudflare.com) → sign up → **Workers & Pages → Create → Hello World** → name `healvio-ai` → **Deploy**.
2. **Edit code** → delete everything → paste all of `ai-server/worker.js` → **Deploy**.
3. **Settings → Variables and Secrets → Add**:
   - `ALLOWED_ORIGINS` (Text): `https://healvio.web.app,https://healvio.firebaseapp.com`
   - `FIREBASE_SERVICE_ACCOUNT` (Secret): open the `.json` file in Notepad → **Ctrl+A, Ctrl+C** → paste.
   - Save / Deploy.
4. Copy the worker link (looks like `https://healvio-ai.yourname.workers.dev`).

### 3.3 Connect the app
In `config.js`:
```
server: "https://healvio-ai.yourname.workers.dev",
vapidKey: "B…your key…",
ai: false
```
Then `firebase deploy --project healvio`. Open Healvio → **Turn on** when it asks about notifications (or Profile → Notifications → Turn on).

### 3.4 Turn on AI (FREE)
AI summary, doubt check, translate and **AI call notes** run on Cloudflare Workers AI. It's free for 10,000 "neurons" a day (about 20 video consults with notes, or about 45 summaries). It resets at 5:30 AM India time, and Cloudflare does not use your data to train AI.
1. Cloudflare → **Workers & Pages → healvioai → Settings → Bindings → Add → Workers AI**.
2. Variable name: `AI` → **Add binding** / **Deploy**.
3. That's it. The app finds the AI by itself. No change to `config.js`.

**AI call notes:** during a video/voice call, each phone turns only its own voice into text (short pieces, quiet moments skipped) and adds it to the chat as "🎙️ said on the call". The audio is never stored. Each person can tap **AI notes** on the call screen to stop it for their voice.

**Optional (paid, better quality):** add `ANTHROPIC_API_KEY` (Secret) from platform.claude.com. The text AI then uses Claude; call notes stay on Workers AI.

### 3.5 Call relay (needed for calls between cities, free up to 1,000 GB a month)
Without it, a call between two mobile networks (for example Bangalore → Kerala) can stay on "Connecting…" and end.
**Free, no card (ExpressTURN, 1 TB a month):**
1. Go to **expressturn.com** → **Sign up** (free) → open the **Dashboard**.
2. Copy the **username**, **password** and the **server** shown (for example `relay1.expressturn.com:3478`).
3. Worker → Variables: `TURN_USERNAME` (Text), `TURN_PASSWORD` (Secret), `TURN_SERVER` (Text, the server) → **Deploy**.

**Or Cloudflare (asks for a card, first 1,000 GB free):** Cloudflare → **Realtime → TURN Server → Create** → Worker → Variables: `TURN_KEY_ID` (Text) and `TURN_KEY_API_TOKEN` (Secret).

Nothing to change in the app. If the direct route fails, the app switches to the relay by itself.

### 3.5b Medicine reminders
Worker → **Settings → Trigger events → Add → Cron trigger → Minute(s): 1** (every minute, `* * * * *`) → **Deploy**. Reminders then arrive on time to the minute. Admin → **System check** shows "Medicine reminders: Working · last check …".
The same trigger sends the **consultation time** alerts (below) even when the doctor's phone is locked.

**Check your worker:** open `https://healvio-ai.yourname.workers.dev/ice`: you should see `iceServers`.

### 3.6 PayPal payments (free test mode)
Patients pay the doctor's fee (after the doctor accepts) and medicine orders (after the store adds the price) with PayPal. The price is always read from the database by your worker, and only your worker can mark something as paid.
1. Go to **developer.paypal.com** → log in with a PayPal account (or sign up, free).
2. **Apps & Credentials** → keep the switch on **Sandbox** → open **Default Application** (or **Create App**) → copy the **Client ID** and the **Secret key**.
3. Cloudflare → **healvioai → Settings → Variables and Secrets → Add**:
   - `PAYPAL_CLIENT_ID` (Text) → the Client ID
   - `PAYPAL_CLIENT_SECRET` (Secret) → the Secret key
   → **Deploy**. The app shows **Pay** buttons by itself. No change to `config.js`.
4. To test a payment: developer.paypal.com → **Testing Tools → Sandbox Accounts** → open the **Personal** account → copy its email and password. Use them in the PayPal window. No real money moves in Sandbox.

**Medicine orders (Stores tab → Order medicines):**
1. Patient: choose the prescription → **Pick up at the store** (pre-booking) or **Home delivery** (door set on a map with GPS) → choose the store → **Send order**.
2. Store (**New** tab): tick ✓ each medicine, type prices (and a delivery fee for delivery) → **Send price to patient**.
3. Patient: **Pay with PayPal** (or pay at the counter / cash at the door).
4. Store (**In progress** tab): pick-up → **Handed over to patient**. Delivery → type who delivers → **Start delivery**: that phone shares its live location and the patient taps **Track live**. Keep Healvio open on the delivery phone, then tap **Delivered**.

**Pay before the consultation:** after the doctor accepts, the patient pays the fee in the app. The doctor's **Start consultation** opens only after payment, so nobody leaves without paying. The doctor can tap **Remind** to send a payment alert, or **Start anyway (free or paid in cash)**. Your worker's Cron trigger also sends "Pay to confirm" alerts 1 hour and 10 minutes before the slot.

**Doctor timings for each day:** doctors don't fill timings at sign-up. On the Queue page, **Today's availability → Set today / Plan other days**: a start time, minutes per consultation and how many consultations (e.g. 10:00 AM, 20 min, 10 → 10:00 AM to 1:20 PM). Sunday is a day off unless set. **Reuse my previous day** (on by default) copies the last day that was set and shows "Copied from …". Booked patients keep their time when a day is changed.

**Consultation timer:** when a consultation starts, the doctor and the patient both see the time passed and the time left (it carries on after a refresh). When the booked minutes are over the doctor gets "Time is up" and has **10 extra minutes**, then a stronger reminder. It never ends by itself; only the doctor ends it. When a consultation runs over, today's next patients are told once: "about 10 minutes late", with their booked time and the expected time.

**Next patient:** when the doctor ends a consultation (early or late), the next patient gets "Please be ready, you're next". The doctor's **I'm ready** button sends "Your doctor is ready for you", and **Start** sends "Your consultation has started": three different alerts.

**My doctors (patients):** tap ♡ on any doctor card, or **Save as my doctor** on a profile, to keep the doctors you like at the top of the home screen for quick booking (as many as you want); the **♥ My doctors** chip shows only them. If the admin terminates a doctor, every patient who saved that doctor gets an alert: "removed from Healvio after a patient report" when the admin ticks that box (it is ticked by itself when a patient report about the doctor exists), otherwise "no longer available". If the doctor is reinstated, they are told the doctor is back.

**App language (patients):** right after login a patient chooses one of 12 languages (English, Hindi, Telugu, Tamil, Kannada, Malayalam, Marathi, Bengali, Gujarati, Punjabi, Odia, Urdu). Every patient screen, button, alert and their prescription (medicine names too) then shows in that language; change it any time in Profile → App language. The app's own words come from the `i18n/` folder (one file per language, no AI needed); names, the problem the patient wrote and prescription details are turned by your worker's free AI once and kept on the phone. Alerts, and the phone pop-ups that arrive while the app is closed, are in the patient's language too: each alert sentence is matched with a ready-made pattern from the `i18n/` files, so doctor names, prices and times stay exactly as they were and no AI is needed. Chat messages always stay exactly as people typed them. After this update, a patient opens Healvio once so the phone learns their language for pop-ups. Doctors, stores and admins stay in English, and orders reach the store in English.

**Ratings & reviews (like the Play Store):** the profile shows the average, star bars and the 3 most useful reviews. Tap a star row to see only those reviews, sort by newest, highest or lowest. Names show as "Ravi K.". Doctors can reply to reviews (Profile → My reviews).

**AI summary:** your worker reads the whole chat, what each person said on the call and the prescription, writes the summary (symptoms, what the doctor found, medicines with timing, tests, food and rest advice, warning signs, follow-up), then checks it again against the conversation. It is made by itself when the doctor finishes with a prescription, and the patient gets an alert. Doctors also see a short clinical note (SOAP). Profile → **Language you speak on calls** makes call notes more accurate.

**Refunds:** a patient can cancel a paid visit before it starts ("Cancel & get a full refund"). The doctor, the store or the admin can cancel and refund at any time. The money goes back to PayPal by itself.

**AI extras (free):** "Not sure which doctor you need?" on the patient home, "Paper prescription" (photo read by AI) in Order medicines, and 🔊 Read aloud on the prescription and the AI summary.

Optional variables: `INR_RATE` (rupees per dollar, default 95), `PAY_CURRENCY` (default `USD`), `PAYPAL_ENV` = `live` for real money (then use the **Live** Client ID and Secret).

---

## Video & voice calls (already on)

- During a **live** consultation, tap 📞 or 📹 at the top of the consult room.
- The other phone rings with **Accept / Decline**. With notifications on (Part 3), it rings even when Healvio is closed.
- In the call: **Mute, Camera off, Flip, Chat** (small window so the doctor can type or write the prescription) and **End**.
- Phone-to-phone and encrypted. Never recorded. The chat shows "📹 Video call · 4:12" or "Missed video call".
- The call stays on until the doctor or the patient taps **End**. If the network drops, it shows "Reconnecting…" and reconnects by itself.
- A free relay (Open Relay) is built in so calls connect on mobile data. For your own relay, see Part 3.5.
- Unanswered calls ring for 60 seconds, then show **Call again**.

---

## Part 4 — Publish the website (Route A)

**Firebase Hosting (recommended: Google login works best on the same domain)**
1. Install Node.js LTS from [nodejs.org](https://nodejs.org).
2. In a terminal inside the healvio folder:
   ```
   npm install -g firebase-tools
   firebase login
   firebase deploy --project YOUR_PROJECT_ID
   ```
   This publishes the app *and* the security rules.
3. Your app is live at **https://YOUR_PROJECT_ID.web.app**.
4. Add that address to `ALLOWED_ORIGINS` on the AI worker.

After any change, run `firebase deploy --project YOUR_PROJECT_ID` again.

**Using Netlify instead?** Drag the folder onto [app.netlify.com/drop](https://app.netlify.com/drop). Then add your Netlify address in Firebase → **Authentication → Settings → Authorized domains**.

---

## Part 5 — Everyone can use it on Android now

Share your link (e.g. `https://healvio-xxxx.web.app`) on WhatsApp, by QR code or on posters.

- **Android (Chrome):** open the link → ⋮ → **Install app**. Healvio gets its own icon and opens full-screen.
- **iPhone (Safari):** **Share → Add to Home Screen**.

This works for everyone right away, with no Play Store needed.

---

## Part 6 — Google Play Store (Route B)

### 6.1 Developer account: Organization
Google requires developers of **health apps (such as medical apps) to register as an Organization**. You need:
1. A **registered business**: a company, LLP, partnership or proprietorship. A CA can help.
2. A **D-U-N-S number** for that business from Dun & Bradstreet. Play Console links to the request page, and it can take a few weeks.
3. A [Play Console](https://play.google.com/console) **Organization** account (one-time registration fee), with the business details matching your D-U-N-S record.

Organization accounts don't need the 12-testers-for-14-days closed test that new personal accounts must run.

### 6.2 Make the Android package
1. Go to [pwabuilder.com](https://www.pwabuilder.com), enter your live address, then **Package for stores → Android → Generate**. Use a package ID like `com.yourbusiness.healvio`.
2. Download the zip.
   - Copy `assetlinks.json` to `.well-known/assetlinks.json` inside the healvio folder, then `firebase deploy` again. This hides the browser bar in the app.
   - **Keep the signing key file safe.** Every future update needs it.

### 6.3 Fill in Play Console
- **Upload** the app bundle (.aab).
- **Privacy policy URL:** `https://YOUR-SITE/privacy.html`. Fill in `privacy.html` first.
- **Account deletion URL:** `https://YOUR-SITE/privacy.html#delete-account`.
- **App access:** give reviewers a Gmail test account you created for them (or a test phone number, if SMS is on).
- **Health apps declaration**, **Data safety** form and **Content rating**: answer truthfully. Healvio collects name, phone, email, age, health information in consultations and photos, and doesn't sell data.
- **Store description:** include this line: *"Healvio connects you with registered doctors. It is not a medical device and does not diagnose, treat, cure, or prevent any medical condition. For emergencies, call 112."*

---

## Before real patients use it — checklist

- [ ] `privacy.html`: replace every highlighted item and remove the yellow box.
- [ ] Have a lawyer check the policy and your setup against India's DPDP Act, the IT Rules and the Telemedicine Practice Guidelines.
- [ ] Verify each doctor's registration number with the medical council before you tap **Approve**.
- [ ] Set Firebase and Claude budget alerts.
- [ ] Payments: fees are shown but not collected. Add Razorpay if you'll charge.
- [ ] Turn on Firestore backups (Firestore → Disaster recovery).

---

## Costs (pay-as-you-go)

| Service | What you pay for |
|---|---|
| Firebase | **₹0 on the Spark plan** for Google login, database and hosting (within the free limits). SMS OTP needs the Blaze plan and is charged per SMS. |
| Claude API | Per AI request. Set a spend limit. |
| Cloudflare Workers | Free plan is enough to start. |
| Calls | Free. The optional Cloudflare relay is free up to 1,000 GB a month. |
| Phone notifications | Free (Firebase Cloud Messaging + Cloudflare Worker free plan). |
| Database | Free up to 50,000 reads and 20,000 writes a day (Firebase Spark plan, resets at 1:30 PM India time). Each phone keeps a copy of the data, so opening Healvio again reads only what changed. If Firebase shows "exceeded no-cost limits", alerts, payments and the AI summary pause until the reset: avoid reopening the app on many phones again and again while testing. |
| Google Play | One-time registration fee. |

---

## Legal safety (India's telemedicine rules)

- **Consent:** patients tick "I agree to an online consultation" before every request. The time is saved on the request.
- **Doctor is responsible:** every prescription shows the doctor's name, qualification, registration number, signature and a footer naming the Telemedicine Practice Guidelines (2020) for their system of medicine.
- **Medicines not allowed online:** Allopathy prescriptions with Schedule X or narcotic / psychotropic (NDPS) medicines (for example alprazolam, tramadol, codeine syrups) are blocked, with a clear reason for the doctor.
- **Complaints:** "Report a problem" on every consultation and order goes to Admin → More → Complaints. The admin replies, and the user sees it in Profile → My reports.
- **Terms of Use:** `terms.html` (linked on the login page, the request form and Profile). Have a lawyer review `terms.html` and `privacy.html` before a commercial launch.

## Data model (Firestore collections)

| Collection | What's in it | Who can read it |
|---|---|---|
| `accounts` | Private profile: name, phone, email, age, doctor documents list | The person and admins |
| `public` | Public profile of approved doctors and stores | Everyone logged in |
| `requests` | Consultations: status, slot, queue, emergency, rating, AI summary, `paid` / `refund` (written only by your worker) | That patient, that doctor, admins |
| `requests/{id}/messages` | Chat messages | That patient, that doctor, admins |
| `prescriptions` | Prescriptions | That patient, that doctor, admins |
| `orders` | Prescriptions sent to stores: pick-up or home delivery (address, map point), prices, delivery fee, live location of the delivery phone, paper prescription photo, and `paid` / `refund` (written only by your worker) | That patient, that store, admins |
| `notifications` | In-app alerts | The recipient (admin alerts: admins) |
| `reviews` | Star ratings and remarks | Everyone logged in |
| `slots` | Each doctor's busy times and emergency slots used | Everyone logged in |
| `files` | Certificates (private) and signatures (public) | Owner and admins; signatures for everyone |
| `calls` | Call handshake only (who called whom, when, status). No audio or video is stored. | The two people on the call, admins |
| `pushTokens` | Each person's phone notification addresses | Only that person (and your worker) |
| `pushLog` | Which alerts were already sent (stops duplicates) | Only your worker |
| `reminders` | Medicine reminder times for each prescription, and which doses were taken | Only that patient (and your worker) |
| `reviews` | Star rating, review text, short name ("Ravi K.") and the doctor's reply | Everyone logged in (only the doctor can reply) |
| `system` | Worker health (last reminder check) | Admins |
| `complaints` | "Report a problem" reports and the admin's reply | The person who reported, and admins |
| `admins` | Admin list (added by hand) | Each person can only check themselves |

---

## Troubleshooting

| Message | Fix |
|---|---|
| "SMS login needs the Firebase Blaze plan" | Keep `phoneLogin: false` in `config.js`, or upgrade to Blaze |
| "This sign-in method is off" | Part 2.2: enable Google |
| Google window opens and closes | Allow pop-ups for your site in Chrome, then try again |
| "This website is not listed in … Authorized domains" | Add your site in Authentication → Settings → Authorized domains |
| "The database refused access" | The rules weren't published: Part 2.3, step 3 |
| "Connect Healvio to Firebase" screen | Paste your settings into `config.js` (Part 2.4), save, and open the app through `http://localhost:8080`, not by double-clicking |
| No "Open admin console" in Profile | Part 2.5: the `admins` document ID must exactly match your user ID |
| "AI server refused this website" | Add the exact address to `ALLOWED_ORIGINS` on the worker |
| Phone shows the old version | Close and reopen the app. After big updates, change the number in `healvio-v3` in `sw.js` (for example to `healvio-v4`). |
| "Camera or microphone is blocked" | Tap the lock icon next to the web address → allow Camera and Microphone. On an installed app: Android Settings → Apps → Healvio (or Chrome) → Permissions. |
| Call never rings on the other phone | The consultation must be **live**. With notifications on (Part 3) it rings as a notification when Healvio is closed. |
| Call says "Connecting…" and ends, or "Couldn't connect" (often between two cities or mobile networks) | Set up the free Cloudflare relay (Part 3.5). Admin → System check must show ✅ "Calls between cities". |
| "Couldn't turn on notifications: Registration failed - push service error" | On that phone: Chrome → ⋮ → Settings → Site settings → All sites → healvio.web.app → **Clear & reset**. Open Healvio, log in, tap **Turn on** → Allow. Update Chrome and Google Play services. |
| No medicine reminder alerts | Add the Cron trigger, every 1 minute (Part 3.5b), turn on notifications on the phone, and check the reminder is On in the prescription. |
| No **Pay** button | The doctor must accept first (fee) or the store must add a price (medicines). Check `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` on the worker, then close and reopen Healvio. |
| "PayPal sign-in failed" | The Client ID or Secret is wrong, or you mixed Sandbox and Live keys. Copy both again from the same app. |
| Payments fail, no phone pop-ups, AI summary errors — all at once | These all go through your worker. Open Healvio as admin: **System check → Live check** tries the worker's Google key, database, PayPal and AI right now and says which one is broken and how to fix it. Most common: the `FIREBASE_SERVICE_ACCOUNT` key stopped working (make a new key in Firebase → Project settings → Service accounts and paste it on the worker), or a free daily limit is used up (Firebase database resets at 1:30 PM India time, Cloudflare AI at 5:30 AM). Never put the service account file inside the healvio folder or on GitHub: Google switches off keys it finds in public. |
| No phone notifications | Profile → Notifications must say **On**, then tap **Send test notification** and go to the home screen. Come back: the line under the button says exactly what happened (sent, the database free limit, Google refused and which setting to turn on, or the worker's Google key). A dead phone registration is renewed by itself. The admin System check also shows the result of the last alert sent from that phone. Check `server` and `vapidKey` in `config.js`, and `FIREBASE_SERVICE_ACCOUNT` + `ALLOWED_ORIGINS` on the worker. On iPhone, add Healvio to the Home Screen first. |
| Notifications arrive but don't pop up or ring | Phone setting: press and hold a Healvio notification → **Alerting**, then ⚙️ → turn on **Pop on screen** (Samsung: Pop-up, Xiaomi: Floating notifications, Vivo/Oppo/Realme: Banners) and **Sound**. Turn off Do not disturb and Notification cooldown. Battery → No restrictions. |

---

### Sources
- [Google Play: developer account types (health apps must register as an Organization)](https://support.google.com/googleplay/android-developer/answer/10788890)
- [Google Play: testing requirements for new personal accounts](https://support.google.com/googleplay/android-developer/answer/14151465)
- [Google Play: Health apps declaration](https://support.google.com/googleplay/android-developer/answer/14738291)
- [Google Play: Health Content and Services policy](https://support.google.com/googleplay/android-developer/answer/16679511)
- [Firebase Authentication limits (SMS on the Blaze plan only)](https://firebase.google.com/docs/auth/limits)
- [Firebase release notes](https://firebase.google.com/support/releases)
- [Claude API: Messages](https://docs.claude.com/en/api/messages)
- [PWABuilder](https://www.pwabuilder.com)
