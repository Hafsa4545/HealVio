# Healvio tests

886 automated checks in 40 test suites. All payments, AI, Firebase and push services are replaced by fakes, so the tests never touch real accounts or money.

| Folder | What | Needs |
|---|---|---|
| `browser/` | Two phones in one browser (doctor and patient): login, booking, PayPal checkout, video calls, prescriptions, medicine orders and delivery, consultation timer, 12 languages, alerts, My doctors | Python 3, Playwright, Google Chrome |
| `node/` | The server (`wtest*`: PayPal create/capture/refund, push alerts, AI and the free backup AI, reminders, consultation timer) and the service worker (`swtest*`: offline start, phone pop-ups, pop-ups in the patient's language) | Node.js 22 |

`runall.sh` runs every suite. The scripts were written for our build machine: the paths at the top of each file (for example `/home/claude/healvio-app`) point to the app folder and the test folder, so change them to where you put this repository before running.
