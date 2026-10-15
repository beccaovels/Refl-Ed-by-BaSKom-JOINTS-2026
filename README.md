# [BaSKom @ JOINTS] AI teaching simulator

JOINTS Hackathon 2026 (UGM), team BaSKom. The product name is not decided yet. The UI reads its name from one constant, `APP_NAME` in `frontend/src/lib/config.js`, so it can be changed in one place.

Indonesian teachers rehearse a lesson in a room that looks like a video call. They present their own material, an AI student asks questions live, and afterwards they get a report built from evidence in their own words. It runs locally; nothing is deployed.

- [Product overview](#product-overview)
- [Personas: Bu Rina and Bu Lina](#personas-bu-rina-and-bu-lina)
- [Current scope](#current-scope)
- [Features and user flow](#features-and-user-flow)
- [Long-term vision](#long-term-vision)
- [Tech stack and architecture](#tech-stack-and-architecture)
- [Project structure](#project-structure)
- [Setup and running](#setup-and-running)
- [Environment configuration](#environment-configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Working together](#working-together)

## Read first

| File | What it is |
|---|---|
| `docs/team-guide.md` | **Start here.** Setup, daily routine, where every page and module lives |
| `docs/prd.md` | The PRD (v2, 13 Oct). Product, scope, acceptance criteria |
| `docs/plan.md` | The full plan: context, architecture, grading, schedule, who does what |
| `docs/api-contract.md` | The agreement between frontend and backend. Change it before changing code |
| `docs/delivery-grading.md` | Grading and feedback rules |
| `docs/ai-pipeline.md` | How speech-to-text, the AI student, metrics and scoring fit together |
| `docs/todo.md` | What is still unproven |

## Product overview

### The problem

Teachers in well-resourced schools get coaching and classroom observation. Most teachers across Indonesia do not, especially outside big cities. Many have low pay and a heavy administrative load, and teach from one modest laptop. Without anyone to watch them practise, the step from reading slides aloud to teaching an engaging lesson is hard to take alone.

The framing is **unequal access to coaching**, not unequal teachers.

### What the product does

It turns micro-teaching into something a teacher can do alone, at any time:

1. The teacher chooses a lesson and, optionally, uploads their material (PDF or pictures).
2. In a video-call-style room they teach it out loud. Their speech is transcribed live, and an AI student called **Refl** asks questions about what was just said and the material on screen.
3. Afterwards they get a report:
   - **What worked.**
   - **What we noticed.**
   - **Up to three ideas you could try.** Each idea comes with ready-to-use text in Bahasa Indonesia.

   Every qualitative point quotes the teacher's own words with a timestamp.

**Stance:** a rehearsal partner and a mirror, not a judge. Feedback is input the teacher may ignore.

### Principles that are never broken

These hold across the whole product.

- **No eye-contact scoring and no emotion labels.** A calm, serious teacher can reach the top score.
- **Equipment is never scored.** That covers lighting, camera quality and equipment.
- **The camera is optional.** A full report works from audio alone.
- **Video never leaves the browser.** Only small JSON signal bins and audio pieces are uploaded.
- **Feedback is kind and quoted.**
  - It follows the order: what worked, what we noticed, an idea to try.
  - At most three ideas.
  - No "kurang", "lemah" or "seharusnya" (nor "lacking", "poor", "weak", "should").
  - No comparison with other teachers.
  - Quotes not found in the transcript are dropped.
- **Ideas need no extra preparation, materials or devices.**
- **The teacher owns the data.** No individual scores go to principals.
- **The rubric is "aligned with" the Kemendikdasmen guides.** It is never called "the official rubric".

## Personas: Bu Rina and Bu Lina

The login screen offers two demo accounts. Both are defined in `frontend/src/lib/personas.js`:

| Account | Label on the login screen | Meaning |
|---|---|---|
| **Bu Rina** | "Sudah pernah berlatih" | An experienced teacher who has practised with the tool before |
| **Bu Lina** | "Pengguna baru" | A teacher with no prior experience of the tool |

The two personas differ in their starting data. Both use the same simulator and the same report.

| Persona | Starting data |
|---|---|
| Bu Rina | Two sample reports and two planned practices |
| Bu Lina | An empty history |

Each persona's history is stored separately in the browser (`localStorage` key `gema-demo-v1:<user id>`). Logging out and back in as the other persona switches the history.

### Bu Rina: experienced teacher

**Journey**

1. **Login.** Bu Rina picks her account. The backend creates or finds the user `bu.rina@demo.local`. There is no password.
2. **Dashboard.** It greets her with "Selamat datang kembali!".
   - Her latest report is shown with its score.
   - Her planned practices are listed.
   - The "start a session" action is the main button.
3. **History and Performance.** These already contain two example reports (scores 82 and 76), clearly marked as examples, so she can see how progress looks.

   Performance shows score trends per card across her sessions.
4. **Simulator.** She goes from Setup to the device check, then to the Room, then to the report. This is the same flow as for Bu Lina (see [Features and user flow](#features-and-user-flow)).
5. **Report and progress.** A new report is added to her history next to the samples, and the trends update. "Latih lagi" on a report reopens Setup with the same lesson filled in.

### Bu Lina: new teacher

**Journey**

1. **Login.** Bu Lina picks her account. The backend creates or finds `bu.lina@demo.local`.
2. **Dashboard.** It greets her with a first-time welcome ("Selamat datang di …"). History and planned practices show empty states that point to starting a first session.
3. **Simulator.** She follows the same Setup, device check, Room and report flow.
   - In the Room, Refl greets her once and says the first question comes after about 75 seconds of speaking.
   - The camera is optional; a microphone is required.
4. **Report and progress.** Her first report becomes the first entry in History and on the Performance page; trends build up as she practises more.

### Comparison

| | Bu Rina (experienced) | Bu Lina (new) |
|---|---|---|
| Login label | "Sudah pernah berlatih" | "Pengguna baru" |
| Demo email (created on login) | `bu.rina@demo.local` | `bu.lina@demo.local` |
| History on first login | Two sample reports (82 and 76) | Empty |
| Planned practices on first login | Two | None |
| Dashboard greeting | "Selamat datang kembali!" | First-time welcome |
| Performance trends | Visible straight away from the samples | Appear after her own sessions |
| Simulator, AI student, report | Same | Same |
| Plan (tier) | Free (all six cards are scored for every teacher) | Free |
| Persona-specific guidance or difficulty | Not implemented | Not implemented |

## Current scope

**The supported content is Mathematics, Grade 10 (Matematika Kelas X, Fase E), chapter Probability (Bab 7 Peluang).**

| Part | Detail |
|---|---|
| Profile file | `backend/app/profiles/matematika-fase-e.yaml` |
| Source | The *Buku Panduan Guru Matematika Kelas X* |
| What it provides | Clarity parameters, documented misconceptions with page numbers, the student persona (age 15–16), question depth levels and context seeds |

Two things to know:
- **The profile is marked `tested: false`.** It has no strong and weak sample lessons yet. `GET /api/profiles` therefore hides it unless `SHOW_UNTESTED_PROFILES=true` is set in `backend/.env`. Set it to `true` to run a lesson (see [Troubleshooting](#troubleshooting)).
- **Mathematics lessons use this profile.** The Room picks the profile by subject, so a Matematika lesson is taught with the Kelas X Peluang profile and its documented misconceptions.

Other subjects and grades are future direction only (see [Long-term vision](#long-term-vision)).

## Features and user flow

**Flow:** Login → Dashboard → Setup → Periksa perangkat (device check) → Ruang latihan (Room) → Refleksi (report) → History / Performance.

Status key: **Implemented** = works end to end in the app. **Limited** = works with a stated restriction. **Planned** = described in the PRD, not built.

### Login and Dashboard

| Feature | Status | Notes |
|---|---|---|
| Demo login with two personas | Implemented | No password and no real authentication, by design. The frontend sends `X-User-Id` on every request |
| Dashboard | Implemented | Greeting, latest report, planned practices, start button |
| Plan label and locked cards (Free / Institutional) | Limited | Users are created on the Free tier. Every card is scored for every teacher, so `locked` is always `false` |

### Setup

| Feature | Status | Notes |
|---|---|---|
| Choose class, subject, chapter and sub-chapter | Limited | Only subjects with a backend profile are offered. The chapter list is defined in `frontend/src/lib/data.js` |
| Upload material | Implemented | Up to 10 files per lesson: PDF up to 20 MB, JPEG or PNG up to 8 MB, 50 MB total, 300 PDF pages. Text in pictures is read by the LLM in the background. Continuing without material works |

### Room

| Feature | Status | Notes |
|---|---|---|
| Device check | Implemented | Microphone required, camera optional; a denied microphone blocks entry with a clear message |
| Stage | Implemented | Present a PDF (pdf.js, page controls) or a picture, or share a screen or window. A picker switches between them; with nothing chosen the stage shows the lesson topic. Every page turn is logged; a shared screen is logged as page 0 and never uploaded |
| Live transcript | Implemented | The browser cuts audio at pauses and sends numbered WAV pieces. A repeated number is ignored |
| AI student "Refl" | Implemented | One character in a pop-up with a chime. In demo mode it asks after about 75 s of speech. It can also ask a misconception question, answer the teacher's question to the class, react, ask one follow-up, or nudge after silence |
| Pause, end and capstone | Implemented | "Selesai mengajar" leads to one closing question, then "Simpan sesi", then the report is generated and polled |
| Typed lesson note | Implemented | In Refl's pop-up |
| Voice signals | Implemented | Loudness and pitch in the browser, sent as 10-second bins |
| Camera tile | Implemented | Three sizes and a privacy shield. The video stays in the browser |
| Camera landmark signals (posture, gestures, facing) | Limited | The code exists in `frontend/src/features/simulator/vision/` and is unit-tested, but the Room does not start it. Bins carry voice only, and the delivery card is scored from voice |
| Live HUD (framing and pace indicators) | Planned | |
| Spoken AI student (text to speech) | Planned | A stretch item |

### Report, History and Performance

| Feature | Status | Notes |
|---|---|---|
| Report | Implemented | The overall score and six cards: Ketepatan materi, Alur mengajar, Kejelasan, Keterlibatan murid, Tempo and Suara & ekspresi. Each is 0–100 with a growth label (Mulai tumbuh <50, Berkembang 50–79, Kuat ≥80). It opens with strengths, then what we noticed, quoted evidence and at most three ideas. The transcript is included, collapsed |
| "This is not accurate" button | Planned | The backend endpoint `POST /reports/{id}/flags` exists, and `flagItem` exists in `lib/api.js`. No button calls it |
| History | Implemented | Reads the browser store. A report offers "Latih lagi" (Setup with the same lesson) and "Jadwalkan latihan" |
| Performance | Implemented | Score trends per card across sessions |
| Schedule | Limited | Calendar, upcoming and missed practices, kept in the browser only. No reminders. A practice is "Terlewat" only if its time has passed and it was never started |

### Backend only

| Feature | Status | Notes |
|---|---|---|
| Worked-example photo check (`/api/examples`) | Limited | The endpoint and its tests exist. The frontend does not use it |
| Landing page | Planned | UIUX |
| Evaluation numbers (WER, signal agreement) | Planned | Speech-to-text accuracy and signal agreement on recorded clips |

## Long-term vision

This section is future direction only. None of it is built.

- **Six subject profiles.** Grade X Matematika and Bahasa Inggris; grade XI Matematika Tingkat Lanjut, Bahasa Inggris, Sejarah and Biologi. Each is a data file using the same engine, cards and feedback rules, and each is offered only after passing a strong-vs-weak sample check.
- **Camera delivery signals.** Posture, gestures, facing the class and responsiveness to student questions, after a 3-second calibration. Measured on labelled clips and reported in the deck.
- **An Institutional plan.** Schools buy access and see aggregate usage, never an individual teacher's scores.
- **Spoken AI students.** Browser `id-ID` speech synthesis.
- **Direct PPTX upload.** PowerPoint is exported to PDF today.
- **Validation with real teachers.** At least two teachers rate the suggestions. The tool is positioned as practice between sessions with mentors and peer groups (KKG/MGMP).

## Tech stack and architecture

Verified against `frontend/package.json`, `backend/requirements.txt` and the code. The frontend is plain JS/JSX with plain CSS; only `features/simulator/vision/` is TypeScript.

| Layer | What is used |
|---|---|
| Frontend | React 18.3, Vite 6.4, react-router-dom 6.30 (HashRouter), lucide-react icons, plain CSS (`src/styles/`, tokens in `tokens.css`) |
| Material viewer | pdfjs-dist 4.10 (legacy build, loaded only when needed) |
| Browser signals | Web Audio for loudness and pitch. `@mediapipe/tasks-vision` 0.10.14 for optional camera landmarks |
| Backend | FastAPI with Uvicorn, Python 3.11+, pydantic-settings |
| Database | SQLite (`backend/data/app.db`) via SQLModel. Tables are created on startup; there are no migrations |
| PDF text | PyMuPDF, split per page. The closest passages are found by word overlap |
| Speech-to-text | `backend/app/services/stt.py`: Groq `whisper-large-v3` by default, OpenAI as a fallback, or `fake` for no network |
| LLM | `backend/app/services/llm.py`: Gemini with JSON output, falling back to the next Gemini model when one is busy. OpenAI or `fake` can be chosen instead |

```
Browser (localhost:5173)                              FastAPI (localhost:8000/api)          SQLite
 ├─ mic → WAV pieces cut at pauses ──POST /sessions/{id}/audio──► stt.py → transcript ───► app.db
 │                                   ◄── { segment, event } ──── questions.py (LLM + material text)
 ├─ page turns ─────────────────────POST /sessions/{id}/slides──►
 ├─ voice signals → 10 s bins ──────POST /sessions/{id}/signals─►
 ├─ material files ─────────────────POST /materials/{id}/files──► rag.py (PDF text, picture reading)
 └─ end → capstone → finish ────────GET  /sessions/{id}/report──► metrics.py → scoring.py → evidence.py
```

- Vite proxies `/api` to the backend, so no CORS setup is needed in development.
- Video, camera frames and the shared screen never leave the browser.
- Audio pieces are sent to the speech-to-text provider, and transcript and material text to the LLM provider. These are the only calls that leave the laptop.
- Endpoints and JSON shapes: `docs/api-contract.md`.

## Project structure

```
BaSKom-JOINTS/
├─ README.md  .env.example
├─ docs/                    PRD, plan, API contract, grading, AI pipeline, rubric sources, todo, team guide
├─ design/                  UIUX assets
├─ frontend/
│  ├─ index.html  vite.config.js  package.json  README.md
│  ├─ public/assets/        logo, Refl character, favicons, illustrations
│  └─ src/
│     ├─ main.jsx  App.jsx  login gate, shared store, routes
│     ├─ pages/             Login, Dashboard, Setup, DeviceCheck, Report, History, Performance, Schedule
│     ├─ components/        Shell, Button, Empty, PageHeading, LessonFields, Reminder
│     ├─ context/  hooks/   AppContext; useSchedules, useSupportedSubjects, useDialogFocus
│     ├─ lib/               api, adapt, reportText, data, lesson, device, personas, config (APP_NAME)
│     ├─ features/
│     │  ├─ setup/          MaterialUploader
│     │  └─ simulator/
│     │     ├─ audio/       recorder.js: microphone to numbered WAV pieces
│     │     ├─ room/        Room, RoomHeader, RoomControls, RoomDialogs, RoomAlerts, LessonStage, ReflPopup
│     │     ├─ stage/       StageArea, PdfStage, ImageStage, ShareStage
│     │     └─ vision/      voice and camera signals (TypeScript)
│     └─ styles/            one CSS file per area, tokens.css
├─ backend/
│  ├─ requirements.txt
│  ├─ app/
│  │  ├─ main.py  models.py
│  │  ├─ core/              config, db, auth (X-User-Id)
│  │  ├─ api/               auth, profiles, materials, examples, sessions, audio, signals, reports, schedule
│  │  ├─ schemas/           Pydantic models mirroring the contract
│  │  ├─ services/          stt, llm, questions, rag, examples, metrics, delivery, scoring, rubric, evidence, profiles
│  │  ├─ prompts/           question, answer, reaction, misconception, capstone, rubric, image reading
│  │  └─ profiles/          matematika-fase-e.yaml
│  ├─ tests/                pytest suite
│  └─ data/                 app.db and uploads (git-ignored)
└─ ml/
   ├─ eval/                 provider check and try-out scripts (questions, report, example)
   └─ vision-harness/       standalone page for testing the camera signal code
```

## Setup and running

You need Python 3.11+, Node.js 18+ and npm. Clone the repo outside OneDrive, because syncing `node_modules` and `.venv` causes file locks.

### 1. Backend

macOS / Linux:

```
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env (see below)
uvicorn app.main:app --reload
```

Windows:

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env
uvicorn app.main:app --reload
```

Run `uvicorn` from inside `backend/`. Check that http://localhost:8000/api/health returns `{"status":"ok"}`.

### 2. Frontend

In a second terminal:

```
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173, pick Bu Rina or Bu Lina, and start a session. If the backend runs on another address, start the frontend with `API_TARGET=http://localhost:8001 npm run dev`.

### 3. A first run without API keys

Set `STT_PROVIDER=fake` and `LLM_PROVIDER=fake` in `backend/.env`. The app then runs end to end with canned transcripts, questions and reports, without any key or network access. This is useful for checking the flow; the content is placeholder.

## Environment configuration

Copy `.env.example` (repo root) to `backend/.env`. Never commit `.env` and never share keys in the repo; ask the lead privately for keys, or create your own free-tier keys.

| Variable | Purpose | Default in `.env.example` |
|---|---|---|
| `STT_PROVIDER` | `groq`, `openai` or `fake` | `groq` |
| `LLM_PROVIDER` | `gemini`, `openai` or `fake` | `gemini` |
| `GROQ_API_KEY` | Groq key for speech-to-text | empty, fill in |
| `GEMINI_API_KEY` | Google AI Studio key for the LLM | empty, fill in |
| `OPENAI_API_KEY` | Only if a provider is set to `openai` | empty |
| `STT_MODEL` | Speech-to-text model | `whisper-large-v3` |
| `LLM_MODEL` | LLM model; empty uses the code's default Gemini list | see file |
| `LLM_VISION_MODEL` | Tried first when reading a picture; empty means `LLM_MODEL` | see file |
| `DATABASE_URL` | SQLite file | `sqlite:///./data/app.db` |
| `UPLOAD_DIR` | Where uploaded material is stored | `./data/uploads` |
| `FRONTEND_ORIGIN` | Allowed origin | `http://localhost:5173` |
| `DEMO_MODE` | Short question interval for demos | `true` |
| `SHOW_UNTESTED_PROFILES` | Offer profiles not yet marked tested. **Set to `true`** to use the Matematika Kelas X profile | `false` |

## Testing

```
cd backend
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pytest
```

The suite uses the `fake` providers, so it needs no keys or network. It covers:
- metrics from fixed timestamps;
- the evidence check dropping fabricated quotes;
- the single retry on invalid LLM output;
- banned words and the three-idea limit;
- material upload limits and session lifecycles.

It had 214 passing tests at the time of writing.

Other checks:
- **Frontend build:** `cd frontend && npm run build`.
- **Real providers:** from `backend/` with the venv active, `python ../ml/eval/check_providers.py` (add a WAV path to also test speech-to-text) checks that your keys work.
- **Camera signal code:** `ml/vision-harness/` (see its README).
- **Manual checks:** the browser network tab during a lesson should show only audio pieces and small JSON, never video frames.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Room says "Belum ada profil untuk mata pelajaran …" | The Matematika Kelas X profile is hidden by default. Set `SHOW_UNTESTED_PROFILES=true` in `backend/.env` and restart the backend |
| `ModuleNotFoundError: No module named 'app'` | `uvicorn` was started outside `backend/`. Run `cd backend` first |
| Frontend shows network errors or 404 on `/api/...` | The backend is not running on port 8000. Start it, or set `API_TARGET` |
| Transcript never appears | Check the microphone permission in the browser and the `STT_PROVIDER` and key. Use `fake` to rule out the provider |
| Questions or reports fail, or are slow, on Gemini | The free tier is busy or over quota. The code tries the next Gemini model automatically; wait, or switch `LLM_PROVIDER` |
| A report shows a short notice instead of scores | The lesson had fewer than about 40 transcribed words. Speak for longer |
| 413 or 400 on upload | The file is over a limit (PDF 20 MB, picture 8 MB, 50 MB or 10 files per lesson, 300 pages), or it is not a real PDF, JPEG or PNG |
| Old data or schema errors after pulling | Stop the backend and delete `backend/data/app.db`. It is recreated on startup; local sessions are lost |
| A persona's history looks wrong | It lives in the browser's `localStorage` (`gema-demo-v1:<user id>`). Clear site data to reset it |
| Camera is denied | Allowed: the session continues with audio only. A denied microphone blocks the start, by design |

## Working together

- **Branches.** `main` always runs. Work on `name/feature`, open a pull request, and merge at least daily.
- **Ownership.** Stay inside the folders you own (see `docs/team-guide.md`).
- **The contract first.** Any change to an endpoint or JSON shape goes into `docs/api-contract.md` in the same change.
- **Never committed.** `.env`, `backend/data/` and the database.
- **Source PDFs.** The PDFs in `docs/references/` are git-ignored because of their size. Get them from the team drive.
