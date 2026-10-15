# Team guide: how to work in this repo

For the four of us. Read this once after cloning. It covers setup, the daily routine, where every page and module lives, and how to use Claude Code (or another AI tool) here.

Files marked *(to create)* do not exist yet. The name and place are the agreed ones, so create them there.

## 1. Set up once

1. **Clone outside OneDrive**, for example `C:\dev\BaSKom-JOINTS`. Inside OneDrive, `node_modules` and `.venv` get locked while syncing.
2. **Backend** (Python 3.11+):
   ```
   cd backend
   python -m venv .venv
   .venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   copy ..\.env.example .env       # macOS/Linux: cp ../.env.example .env
   uvicorn app.main:app --reload
   ```
   Open http://localhost:8000/api/health. It returns `{"status":"ok"}`. http://localhost:8000/docs lists every endpoint that exists so far and lets you try them.
3. **Keys.** The `.env` file lives in `backend/` and is never committed. Fill in `GROQ_API_KEY` (console.groq.com) and `GEMINI_API_KEY` (aistudio.google.com); both have a free tier. `OPENAI_API_KEY` is the fallback and comes from the lead, privately.
4. **Frontend:**
   ```
   cd frontend
   npm install
   npm run dev
   ```
   Open http://localhost:5173. If `frontend/package.json` does not exist yet, the frontend has not been scaffolded: see "Scaffolding the frontend" at the end. Only one person does that, once.
5. **Tell your AI tool who you are.** Create a file `CLAUDE.local.md` in the repo root (it is git-ignored, so it stays on your laptop) with one line, for example:
   ```
   I am BE+FE 1. I own the Simulator Room.
   ```
   Claude Code reads it and then knows which folders are yours.
6. **Source PDFs** in `docs/references/` are not in git (59 MB). Get them from the team drive if you need them; most people will not.

## 2. Every day

1. `git checkout main` then `git pull`.
2. `git checkout -b yourname/what-you-are-doing`, for example `dina/audio-upload`.
3. Work inside the folders you own (section 3).
4. Before you open a pull request: the backend starts, `pytest` passes, the frontend builds.
5. Push your branch, open a pull request, merge the same day. Small and often beats big and late.
6. Morning check-in, 10 minutes. The lead updates "Today's goal" in `CLAUDE.md`.

**The contract comes first.** `docs/api-contract.md` is the agreement between frontend and backend. If you need a new endpoint or a changed field, edit that file in the same pull request and say so in the team chat. Frontend and backend can then be built at the same time without waiting for each other.

**Files that everyone touches**, so keep edits to one or two lines and merge quickly:

| File | What you add |
|---|---|
| `backend/app/main.py` | one `include_router` line per router |
| `backend/requirements.txt` | one line per package |
| `frontend/package.json` | via `npm install <package>` |
| `frontend/src/App.tsx` *(to create)* | one route per page |
| `frontend/src/lib/api.ts` *(to create)* | one function per endpoint |
| `docs/api-contract.md` | the endpoint you changed |

## 3. Where everything lives

### Page by page

Each row is one screen: the files that draw it, the endpoints it calls, the backend file that answers, and the tables behind it.

| Page and route | Frontend files | Endpoints | Backend file in `app/api/` | Tables | Owner |
|---|---|---|---|---|---|
| Landing `/` | `pages/Landing.tsx` | none | none | none | UIUX |
| Login (a small name + email form) | on Landing or Dashboard | `POST /auth/login` | `auth.py` | `users` | BE+FE 2 |
| Dashboard `/dashboard` | `pages/Dashboard.tsx` | `GET /sessions` | `sessions.py` | `sessions`, `reports` | BE+FE 2 |
| Setup `/setup` | `pages/Setup.tsx` | `GET /profiles`, `POST /materials`, `POST /materials/{id}/examples`, `GET /materials/{id}/examples`, `POST /examples/{id}/confirm`, `POST /sessions` | `profiles.py`, `materials.py`, `sessions.py` | `materials`, `material_chunks`, `worked_examples`, `sessions` | BE+FE 2 |
| Simulator Room `/room/:sessionId` | `pages/Room.tsx`, `features/simulator/` | `GET /sessions/{id}`, `GET /materials/{id}/file`, `GET /materials/{id}/examples`, `GET /examples/{id}/file`, `POST /materials/{id}/examples`, `POST /examples/{id}/confirm`, `POST /sessions/{id}/audio`, `/slides`, `/signals`, `/end`, `/finish` | `audio.py`, `signals.py`, `sessions.py`, `materials.py` | `transcript_segments`, `questions`, `slide_events`, `signal_bins`, `worked_examples` | BE+FE 1 (vision: AI lead) |
| Report `/report/:sessionId` | `pages/Report.tsx`, `features/report/` | `GET /sessions/{id}/report`, `POST /reports/{id}/flags` | `reports.py` | `reports`, `feedback_flags` | BE+FE 2 |
| History `/history` | `pages/History.tsx`, `features/history/` | `GET /sessions` | `sessions.py` | `sessions`, `reports` | BE+FE 2 |
| Schedule `/schedule` | `pages/Schedule.tsx`, `features/schedule/` | `GET /schedule` | `schedule.py` | `schedule` | BE+FE 2 |

Frontend paths are under `frontend/src/`. All endpoints are under `http://localhost:8000/api`.

### Frontend: `frontend/src/`

```
pages/        one file per screen. Thin: layout and routing only, logic lives in features/
components/   shared UI used by more than one page (buttons, cards, score badge)
features/
  simulator/
    audio/    microphone capture, pause detection, WAV encoding, upload queue with retry   BE+FE 1
    stage/    material viewer (pdf.js), next/previous page, page-turn logging; the switch
              between "Materi" and "Papan tulis" (photos of the teacher's own working)     BE+FE 1
    room/     call layout, camera tile, AI student tiles, transcript panel, HUD            BE+FE 1
    vision/   MediaPipe worker, features, calibration, 10 s bins                           AI lead
  report/     report sections, feedback item, "this is not accurate" button                BE+FE 2
  history/    session list, trend arrow                                                    BE+FE 2
  schedule/   static list                                                                  BE+FE 2
lib/
  api.ts      (to create) the only place that calls fetch. Adds the X-User-Id header
  types.ts    (to create) TypeScript types copied from docs/api-contract.md
  config.ts   (to create) APP_NAME, the one constant the UI reads the product name from
styles/       Tailwind entry and design tokens from design/
```

Rules of thumb:
- A component never calls `fetch` itself. It calls a function from `lib/api.ts`.
- The product name is not decided. Never type a name into a component; import `APP_NAME` from `lib/config.ts`.
- The Room page puts the pieces together; each folder under `simulator/` works without knowing about the others. For example `vision/` hands the room a list of bins, and the room sends them.
- Text the teacher reads is in Bahasa Indonesia.

### Backend: `backend/app/`

```
main.py       creates the app, CORS, includes the routers
models.py     database tables (SQLModel). The database file is created on startup            BE+FE 2
core/
  config.py   settings read from .env, and APP_NAME                                           BE+FE 2
  db.py       engine and get_session                                                         BE+FE 2
  auth.py     (to create) reads the X-User-Id header and returns the user                    BE+FE 2
schemas/      Pydantic request and response shapes, one file per api file, same field names
              as docs/api-contract.md                                                        BE+FE 2
api/          one file per group of endpoints: auth, profiles, materials, sessions, audio,
              signals, reports, schedule. Thin: check input, call a service, save, reply     BE+FE 2
services/     the AI pipeline                                                                AI lead
  stt.py        transcribe(): the only code that calls a speech-to-text provider
  llm.py        generate_json(): the only code that calls an LLM provider
  rag.py        split the PDF into chunks, find the chunks closest to the transcript
  examples.py   a photo of the teacher's handwritten working: read it, let the teacher confirm, then check
  questions.py  decide when to ask, build the question, misconception, capstone, nudge
  metrics.py    pace, pauses, questions asked, reading share, time per slide (no LLM)
  scoring.py    build the report: metrics, LLM levels per parameter, evidence check, card scores
  rubric.py     the six cards, their parameters and weights, as data
  report_schema.py  ReportOut: the Report shape as a Pydantic class
  evidence.py   drop any quote that is not the teacher's own words, said or written; catch banned words
prompts/      prompt texts as files, never inside Python strings                             AI lead
profiles/     one YAML file per subject and phase                                            AI lead
```

`backend/tests/`: each person writes tests for their own code. `backend/data/` holds the database and uploads and is git-ignored.

Rules of thumb:
- **Tables** (`models.py`) are what is stored. **Schemas** (`schemas/`) are what goes over the network. They are different classes on purpose; an endpoint never returns a table object directly.
- An `api/` function contains no AI logic and never imports a provider SDK. It calls a function in `services/`.
- Nothing outside `stt.py` and `llm.py` talks to Groq, Gemini or OpenAI. That is what lets us switch provider in `.env`.

### What happens on the two main requests

**One audio piece during the lesson**

```
audio/ upload queue ──POST /sessions/{id}/audio──► api/audio.py
                                                     ├─ seq already stored? return the stored reply
                                                     ├─ services/stt.py        → text
                                                     ├─ save transcript_segments
                                                     ├─ services/questions.py  → a question, or nothing
                                                     └─ reply { seq, segment, event }
room/ shows the text in the transcript panel and, if event is not null, the AI student's question
```

**The report after the lesson**

```
Room ──POST /sessions/{id}/finish──► api/sessions.py starts services/scoring.py in the background
Report page ──GET /sessions/{id}/report──► 202 pending ... 200 Report   (ask again every 2 s)
scoring.py: metrics.py → llm.py with the rubric prompt and profile → evidence.py → save reports
```

### Where the two sides meet

The whole AI side, file by file, with the request flows and endpoint sketches, is in `docs/ai-pipeline.md`. Read it before writing an endpoint that calls a service.

`api/` (BE+FE 2) and `services/` (AI lead) are written by different people, so the function names are agreed up front. Proposed, to confirm at the first check-in:

| Function | Called from | Returns |
|---|---|---|
| `stt.transcribe(wav_bytes)` | `api/audio.py` | text, or `""` when there is no speech (then `segment` is null) |
| `questions.next_event(db, session_id, now_ms)` | `api/audio.py`, on every chunk, after saving the segment. `now_ms` is the chunk's `end_ms` | an `Event` dict or `None`; the question is already saved |
| `questions.capstone(db, session_id)` | `api/sessions.py` (`/end`) | an `Event` dict; already saved |
| `rag.index_material(db, material_id)` | `api/materials.py` after saving the file and the `materials` row | nothing; fills `material_chunks` |
| `scoring.build_report(db, session_id)` | `api/sessions.py` (`/finish`) | the complete `Report` dict, already validated; the endpoint stores it whole in `reports.data` and copies `overall.score` to `reports.overall_score`. Takes 10–40 s, so run it in the background |
| `profiles.list_tested()` | `api/profiles.py` | the profile list, in the shape of `GET /profiles` |
| `examples.add(db, material_id, filename, path)` | `api/materials.py` (`POST /materials/{id}/examples`), after saving the image file | the new `WorkedExample` row with its `page`; status `reading` |
| `examples.read(db, example_id, subject="")` | the same endpoint, in the background (10–30 s) | the row; never raises for a bad photo or a busy provider, the status says what happened |
| `examples.confirm(db, example_id, question=None, steps=None, final_answer=None, subject="")` | `POST /examples/{id}/confirm`. Pass only the fields the teacher sent | the row with its check; `ValueError` when there is nothing to confirm (answer 400). About 5–15 s |
| `examples.for_material(db, material_id)` | `GET /materials/{id}/examples` | the rows in page order |
| `examples.public(row)` | every endpoint that returns an example | the `Example` dict of the contract |

All of these exist in `backend/app/services/` and return the contract's shapes. `db` is the SQLModel session from `get_session`. They raise `ValueError` for an unknown id, and `stt.STTError` / `llm.LLMError` when a provider fails.

The report is real: metrics are computed, the LLM rates each parameter with a quote, and every quote is checked against the transcript. The frontend computes nothing; every score, label and text is in the `Report`. Its shape is the Pydantic class `app.services.report_schema.ReportOut`, which the reports endpoint can use as `response_model`. To see a report without a frontend, run `python ../ml/eval/try_report.py` from `backend/`.

`questions.next_event` returns at most one event per audio chunk, of six kinds (table in `docs/api-contract.md`): a student asks (`regular`, `misconception`), answers the teacher's question (`answer`), shows the answer landed or asks one follow-up (`reaction`), plus `nudge` and `capstone`. The endpoint passes the dict through unchanged. To watch a whole lesson's worth of events without a frontend, run `python ../ml/eval/try_questions.py` from `backend/`.

**Voice and camera signals** are one call for the room, from `frontend/src/features/simulator/vision/index.ts`:

```ts
const signals = await startSignals({ stream, video, now, onBin })  // video: omit when the camera is off
await signals.calibrate()   // optional: 3 s of "sit how you teach"
// ...lesson: every 10 s onBin(bin) fires; send bins to POST /sessions/{id}/signals...
signals.stop()
```

`now` must return milliseconds since the lesson started, the same clock the audio chunks use. The folder needs one package: `npm install @mediapipe/tasks-vision@0.10.14`. Until the frontend project exists, the code is typechecked and tested from `ml/vision-harness/` (`npm install`, `npm run check`), and `npm run dev` there opens a page that shows the live signals from a webcam, the microphone alone, or a recorded clip.

**Handwritten worked examples ("Papan tulis").** A teacher can photograph a question and their own working, in Setup or during the lesson, and show it on the main stage in place of the slide. Who builds what:

- **BE+FE 2:** the four endpoints in `docs/api-contract.md` (they only call the `examples.*` functions above), the Setup upload with the confirm card, and the "Contoh soal" section of the Report from `report.examples`.
- **BE+FE 1:** the stage switch between "Materi" and "Papan tulis", an add-photo button in the room, a one-tap confirm card that never interrupts the lesson, and a `POST /sessions/{id}/slides` with the photo's `page` whenever it goes on stage.
- **The confirm card** shows "Apakah ini yang Anda tulis?" with the question, each step and the final answer in editable fields, steps with `unclear: true` highlighted, and two actions: "Ya, sesuai" (send `{}`) and save edits (send the fields). The check appears only after that. Never show a check, or hint at one, before the teacher confirms.
- With `LLM_PROVIDER=fake` a sample reading comes back (one step marked unclear) and the check agrees, so all of this can be built with no key. To try a real photo without a frontend: `python ../ml/eval/try_example.py photo.jpg --confirm` from `backend/`.

The `questions` table gained three optional columns (`level`, `reply_to`, `satisfied`), there is a new `worked_examples` table, and `materials.filename` and `path` may now be empty. SQLite does not change an existing file, so delete `backend/data/app.db` once after pulling; it is recreated on startup.

To work with no API keys at all, set `STT_PROVIDER=fake` and `LLM_PROVIDER=fake` in `backend/.env`. While no profile is marked `tested` yet, `profiles.list_tested(include_untested=True)` shows them for local development.

## 4. Adding something

**A new endpoint**
1. Write it in `docs/api-contract.md`.
2. Add the request and response classes in `backend/app/schemas/`.
3. Add the function to the right file in `backend/app/api/`, using an `APIRouter`.
4. If the file is new, add `app.include_router(<name>.router, prefix="/api")` in `main.py`.
5. Add one function to `frontend/src/lib/api.ts` and its types to `lib/types.ts`.
6. Add a test in `backend/tests/`.

**A new page**
1. `frontend/src/pages/Name.tsx`.
2. One route in `App.tsx`.
3. Anything bigger than layout goes in `features/<name>/`.

**A new subject profile**
1. Copy `backend/app/profiles/matematika-fase-e.yaml` and fill it in. Misconceptions are copied from the teacher's book with page numbers, never made up.
2. Add a strong and a weak sample transcript in `ml/samples/`.
3. Set `tested: true` only once the strong-versus-weak check passes. Until then it does not appear in Setup.

## 5. Using Claude Code here

Open the repo folder in Claude Code. You do not need to explain the project: `CLAUDE.md` loads by itself, together with `docs/plan.md` and `docs/api-contract.md`.

What is already set for you:
- **Claude cannot push.** `git push` and GitHub write commands are blocked in `.claude/settings.json`. You push yourself.
- **Claude is never an author.** No `Co-Authored-By` line, and it commits only when you ask in that message.
- **It asks before editing someone else's folder**, as long as you made `CLAUDE.local.md` in step 5 of setup.

Agents, shared through the repo. Ask for one by name, for example "use the contract-check agent":

| Agent | When to use it | It can change files |
|---|---|---|
| `pm` | Start of the day: where we are against the schedule, and three tasks per person | no |
| `contract-check` | Before every pull request that touches an endpoint or a call to one | no |
| `principles-check` | Before every pull request that touches text the teacher reads, a prompt, or scoring | no |
| `ai-eval` | After changing a prompt, profile, metric or threshold | no (runs tests and scripts) |

Good ways to ask:
- "I'm building the upload queue in `features/simulator/audio/`. Read the Audio section of the contract and write it with retry on network failure."
- "Add `POST /sessions/{id}/slides` following the contract, with a test."
- "Use the contract-check agent on my branch."

**Other AI tools** (Cursor, Copilot, Codex and so on) do not read `CLAUDE.md` or the push block. `AGENTS.md` in the repo root points them to the same rules, but nothing stops them from pushing or signing a commit, so check `git log` before you push.

## 6. Rules that are easy to break by accident

The full list is in `CLAUDE.md` under "Product principles". The ones that most often slip in through generated code or text:

- No eye-contact score, no emotion words ("happy", "nervous", "confident"), no score for lighting or camera quality.
- The camera is optional. Every page works with it off.
- Video frames never go to the backend. Only audio pieces and small JSON.
- Feedback text never uses "lacking", "poor", "weak", "should", "kurang", "lemah", "seharusnya", and never compares teachers.
- Every quote in a report is found in the transcript, or the item is dropped.
- The rubric is "aligned with" the ministry guide, never "the official rubric".

## Scaffolding the frontend (one person, once)

`frontend/` currently holds only the empty folder layout. From the repo root:

```
npm create vite@latest frontend -- --template react-ts
```

Vite will say the folder is not empty. Choose **"Ignore files and continue"**. Do not choose "Remove existing files". Then:

```
cd frontend
npm install
npm install tailwindcss @tailwindcss/vite react-router-dom
npm run dev
```

Add the Tailwind plugin to `vite.config.ts` and `@import "tailwindcss";` to the main CSS file, commit, and push before anyone else starts frontend work, so there is only one `package.json`.
