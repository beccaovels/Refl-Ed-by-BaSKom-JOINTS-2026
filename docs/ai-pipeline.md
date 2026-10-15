# The AI pipeline: what is built, where it lives, and how the backend uses it

For BE+FE 1 and BE+FE 2, from the AI + PM lead. State on Wed 14 Oct, branch `rebecca/ai-pipeline`.

Read this first if you are writing an endpoint, a page or the room. It says what each AI file does, which function your endpoint calls, what comes back, and what you can rely on not changing. The exact JSON shapes are in `docs/api-contract.md`; the scoring rules are in `docs/delivery-grading.md`; open problems are in `docs/todo.md`.

---

## 1. The short version

- **All AI work is done.** It lives in `backend/app/services/`, plus one browser folder for voice and camera signals (`frontend/src/features/simulator/vision/`).
- **Your endpoints only call functions.** No endpoint talks to Groq or Gemini, builds a prompt or computes a score. Each endpoint checks its input, calls one service function, saves, and replies. The functions you need are listed in section 5.
- **Everything the frontend shows comes ready-made.** Scores, labels and every sentence the teacher reads are in the objects the services return. The frontend lays them out and computes nothing.
- **It runs without API keys.** With `LLM_PROVIDER=fake` and `STT_PROVIDER=fake` in `backend/.env`, every function returns realistic sample data marked "(Contoh)". You can build every page and endpoint today without spending quota.
- **Nothing is trained.** Speech-to-text and the LLM are hosted models (Groq Whisper, Gemini Flash). Face and body landmarks are the pretrained MediaPipe models. Our work is the layer on top: when students speak, what is measured, how it is scored, and the checks that keep feedback honest and kind.

### 1.1 Features and how far each one is

"AI side" is the code in `services/`, `prompts/`, `profiles/` and `vision/`. "Endpoints and screens" is what BE+FE 1 and BE+FE 2 build. **A teacher can use a feature only when both are done.** On 14 Oct the AI side is done for everything below except where stated, and no endpoint or screen exists yet.

| Feature | AI side | Endpoints and screens | Notes |
|---|---|---|---|
| Live transcript | Built: `stt.py` | To build: room audio capture, `POST /sessions/{id}/audio` | Tested on Indonesian clips by hand; word error rate not measured |
| AI students: ask, answer the teacher, react ("satisfied" or one follow-up), capstone, nudge | Built: `questions.py`, six event kinds | To build: the room shows each kind on a student tile | Run end to end on a typed Peluang lesson |
| Questions by grade and misconception questions from the book | Built for Matematika X, Bab 7 Peluang | — | Other five profiles not started (data files only) |
| **Screen sharing, mode A: present the PDF in the app** | Built: the AI reads the text of the page on screen (section 3.4) | To build: pdf.js viewer on the stage, page controls, `POST /sessions/{id}/slides` on every turn | The recommended mode |
| **Screen sharing, mode B: share a screen or window** | Nothing to build: the AI works from what is said (section 3.4) | To build: `getDisplayMedia` shown on the stage, in the browser only | One open decision, see 3.4 |
| **Handwritten worked examples** (photo, confirm, check, score, feedback) | Built: `examples.py`, two scoring parameters, feedback in the report | To build: four endpoints, Setup upload and confirm card, room stage switch and one-tap confirm card, report section | Tried only on printed stand-ins, never on real handwriting |
| Voice and camera signals | Built in the browser: `vision/`, `startSignals()` | To build: the room calls `startSignals()` and forwards bins | Voice path tried in the harness; **camera never run on a real camera** |
| "Suara & ekspresi" card | Built: `delivery.py` | — | Thresholds provisional |
| Report: six cards 0–100, feedback, ideas, metrics, exchanges, worked examples | Built: `scoring.build_report` | To build: `/finish` in the background, `GET /sessions/{id}/report`, the Report page | Live report in 10–40 s |
| Tiers (Free and Institutional) | Built: locked cards in the report | To build: the locked "Upgrade" cards | — |
| History, Dashboard, Schedule | No AI | To build | — |

---

## 2. Architecture

### 2.1 The whole system

```
BROWSER (React, localhost:5173)                      BACKEND (FastAPI, localhost:8000)                   OUTSIDE
                                                     app/api/        app/services/              
 Setup page                                          (BE+FE 2)       (AI lead)                          
  ├─ upload PDF ───────── POST /materials ─────────► materials.py ──► rag.index_material ──────────────┐
  ├─ upload photo ──────── POST /materials/{id}/examples ──────────► examples.add + examples.read ──────┼─► Gemini (reads the photo)
  └─ "Ya, sesuai" ──────── POST /examples/{id}/confirm ────────────► examples.confirm ─────────────────┼─► Gemini (checks the working)
                                                                                                        │
 Simulator Room                                                                                         │
  ├─ audio/ cuts speech at pauses                                                                      │
  │    └─ WAV piece ────── POST /sessions/{id}/audio ──► audio.py ──► stt.transcribe ────────────────┼─► Groq Whisper
  │                                                         │      └► questions.next_event ───────────┼─► Gemini (student's words)
  │    ◄──────────────── { segment, event } ────────────────┘                                          │
  ├─ stage/ page turns ── POST /sessions/{id}/slides ──► sessions.py (store only)                       │
  ├─ vision/ startSignals() runs IN THE BROWSER: MediaPipe + WebAudio                                   │
  │    └─ 10 s bins ───── POST /sessions/{id}/signals ─► signals.py (store only)                        │
  ├─ "Selesai mengajar" ─ POST /sessions/{id}/end ─────► sessions.py ─► questions.capstone ────────────┼─► Gemini
  └─ after capstone ───── POST /sessions/{id}/finish ──► sessions.py ─► scoring.build_report (background) ─► Gemini (rubric)
                                                                                                        
 Report page ──────────── GET /sessions/{id}/report ──► reports.py (reads the stored report)

                                     SQLite: backend/data/app.db (tables in backend/app/models.py)
```

- **Never leaves the laptop:** video and camera frames. The camera is read in the browser; only the numbers in the 10 s bins are sent.
- **Leaves the laptop on purpose:** audio pieces (to Groq, to be transcribed), lesson text (to Gemini), and photos the teacher chooses to upload (to Gemini, scaled down and without the phone's location data).
- **Never stored:** audio after it is transcribed.
- **Never computed in the frontend:** any score. There are none to compute.

### 2.2 Inside `backend/app/services/`

```
                      ┌──────────────── llm.py ─────────────── the ONLY code that calls an LLM (Gemini, OpenAI fallback)
                      │                  stt.py ─────────────── the ONLY code that calls speech-to-text (Groq, OpenAI fallback)
                      │
 questions.py ────────┤ uses: llm, rag, metrics, profiles, prompts/question|answer|reaction|misconception|capstone.md
 examples.py  ────────┤ uses: llm, rag, evidence, prompts/example_read|example_check.md
 scoring.py   ────────┘ uses: llm, metrics, delivery, evidence, examples, rag, rubric, profiles, report_schema, prompts/rubric.md

 rag.py        the teacher's material: PDF pages and photo pages as text chunks; "which text is on screen", "which text is closest"
 metrics.py    numbers from timestamps: pace, pauses, questions, thinking time, reading share, time per slide (no AI)
 delivery.py   the "Suara & ekspresi" card from the signal bins (no AI)
 evidence.py   is this quote really the teacher's words? is this wording allowed?
 rubric.py     the six cards, their parameters and points, as data
 profiles.py   loads backend/app/profiles/*.yaml (one per subject and grade)
 report_schema.py   the Report as Pydantic classes (ReportOut), for your response_model
```

Rules that hold everywhere:
- **Prompts are files** in `backend/app/prompts/`, never strings in Python. Changing what the AI says is a text edit.
- **Subjects are data.** Everything that differs between Matematika X and, say, Biologi XI is in a YAML file in `backend/app/profiles/`. There is no subject-specific code.
- **Every LLM call returns validated JSON.** `llm.generate_json(prompt, Schema)` asks for JSON matching a Pydantic class; a bad reply is sent back once with the error, and a second bad reply raises `llm.LLMError`. Temperature 0.
- **Every AI step has a fallback.** If Gemini is busy, the next Gemini model is tried; if all fail, students say a canned line or stay silent, the photo stays usable, and the room never stalls.

### 2.3 How the backend architecture and the AI meet

| Layer | Folder | Owner | Talks to |
|---|---|---|---|
| HTTP endpoints | `backend/app/api/` | BE+FE 2 | `services/` functions, `models.py`, `schemas/` |
| Request and response shapes | `backend/app/schemas/` | BE+FE 2 | mirror `docs/api-contract.md`; for the report, reuse `services/report_schema.ReportOut` |
| Tables | `backend/app/models.py` | BE+FE 2 (the AI lead added columns, see 6.3) | everyone |
| Settings, database | `backend/app/core/` | BE+FE 2 | `.env` |
| AI pipeline | `backend/app/services/`, `prompts/`, `profiles/` | AI lead | providers, tables |

The contract between `api/` and `services/` is **the function list in section 5**. As long as those signatures and return shapes stay the same, either side can change its insides freely.

---

## 3. The flows, step by step

### 3.1 Setup: material, photos, profile

1. `GET /profiles` → `profiles.list_tested()`. **Note:** the maths profile is still `tested: false` (it becomes true once its strong-versus-weak check passes), so this returns an empty list. While developing, call `profiles.list_tested(include_untested=True)`.
2. `POST /materials` (PDF optional) → save the file to `backend/data/uploads/`, create the `materials` row with `page_count`, then call `rag.index_material(db, material_id)`. Without a PDF, still create an empty material: photos need somewhere to live.
3. `POST /materials/{id}/examples` (a photo) → save the file, `examples.add(...)` returns the row with its `page` (numbered after the PDF's last page). Reply 202 at once, then run `examples.read(db, example_id, subject)` in the background (10–30 s).
4. The Setup page polls `GET /materials/{id}/examples` until `status` is no longer `reading`. With `unconfirmed`, it shows "Apakah ini yang Anda tulis?" and the reading in editable fields.
5. `POST /examples/{id}/confirm` → `examples.confirm(db, example_id, question, steps, final_answer, subject)`, passing only the fields the teacher sent. This is when the working is checked (5–15 s). Returns the example with its `check`.
6. `POST /sessions` → create the `sessions` row with `material_id`.

### 3.2 The room, every audio piece

```
POST /sessions/{id}/audio   (seq, start_ms, end_ms, WAV file)
  1. seq already stored for this session?  → return the stored reply, do nothing else
  2. text = stt.transcribe(wav_bytes)       → "" means no speech: segment is null
  3. if text: save a transcript_segments row (seq, start_ms, end_ms, text)
  4. event = questions.next_event(db, session_id, now_ms=end_ms)   → dict or None, already saved
  5. reply { seq, segment, event }
```

- `next_event` decides, in plain code, whether a student speaks now: react to the teacher's answer, answer the teacher's question, ask a question (misconception once per lesson, otherwise regular), or a quiet nudge after 30 s of silence. Only the wording comes from Gemini, with a 12 s limit.
- The event kinds and what the room shows for each are in the contract's table (`regular`, `misconception`, `answer`, `reaction`, `capstone`, `nudge`).
- Expect 1–3 s for transcription and up to about 6 s more when a student speaks. The room should keep recording while it waits.

### 3.3 The room, alongside the audio

- **Page turns.** Every turn, and every switch to or from a photo, sends `POST /sessions/{id}/slides { page, t_ms }`. Store it; no service call. The AI students and the report read these rows to know what was on screen.
- **Signals.** `startSignals()` from `frontend/src/features/simulator/vision/index.ts` runs in the browser and calls `onBin(bin)` every 10 s. The room forwards bins to `POST /sessions/{id}/signals`. Store them; no service call.
- **A photo mid-lesson.** Same endpoints as Setup. When reading finishes, show a small one-tap card ("Ya, ini tulisan saya") that never interrupts. If the teacher ignores it, the photo is still shown and still used by the AI students, but it is not checked or scored.

```ts
const signals = await startSignals({ stream, video, now, onBin })  // leave out `video` when the camera is off
await signals.calibrate()   // optional, 3 s "sit how you teach"
// ... every 10 s onBin(bin) fires: POST it ...
signals.stop()
```

`now` must return milliseconds since the lesson started, the same clock the audio uses.

### 3.4 Screen sharing: what the AI does in each mode

The room looks like a video call, and the teacher shows their material the way they would share a screen on Zoom. The PRD offers two modes; the AI behaves differently in each.

| | Mode A: present the PDF in the app (recommended) | Mode B: share a screen or window |
|---|---|---|
| How | The PDF uploaded in Setup is drawn on the stage with pdf.js, with next/previous and arrow keys | `navigator.mediaDevices.getDisplayMedia()`; the shared screen is drawn on the stage |
| What goes to the backend | `POST /sessions/{id}/slides { page, t_ms }` on every turn | Nothing. The shared screen is shown in the browser only and is never uploaded, like the camera |
| AI students | Ask about the slide on screen (`rag.page_text`) and the parts of the PDF closest to what is being said (`rag.closest_chunks`) | Ask about what the teacher said, from the transcript alone |
| Report | Everything, including "own words vs reading" and time per slide | Everything except "own words vs reading" and time per slide, which are marked unavailable and do not lower the score |
| Handwritten photos | Switch the stage to the photo and send its `page` | Same: a photo is uploaded and shown on the stage like in mode A |
| AI work needed | None, it is built | None for the basic mode |

Nothing in mode B needs a new endpoint, because the AI simply has no slide text. **One open decision for mode B:** when the teacher has *also* uploaded a PDF but is sharing their screen, the backend assumes page 1 is on screen whenever no slide event has been sent. Until this is decided, create a mode B session with `material_id: null` if no photos are used. The proposed fix is that the room sends `{ page: 0 }` when it switches to the shared screen, and the AI reads page 0 as "no slide text". It is a small change (one contract line, one test) and will be made only once the team agrees.

Reading the text of a shared screen (capturing frames and recognising the text) is not built and is on the roadmap. It would mean sending screen images to Gemini, which the privacy rule currently avoids.

### 3.5 Ending and the report

1. "Selesai mengajar" → `POST /sessions/{id}/end` → `questions.capstone(db, session_id)` returns one closing question.
2. After the teacher answers → `POST /sessions/{id}/finish` → reply 202, then in the background: `report = scoring.build_report(db, session_id)`, store it whole in `reports.data`, copy `report["overall"]["score"]` to `reports.overall_score`. Takes 10–40 s.
3. The Report page polls `GET /sessions/{id}/report`: 202 while pending, 200 with the stored report, 500 if generation failed (`llm.LLMError` when no provider answered).

What `build_report` does, in order:
1. `metrics.compute()` measures pace, pauses, questions, thinking time, reading share and time per slide from the timestamps.
2. One Gemini call reads the transcript, the slides shown and any confirmed worked examples, and returns a 1–5 level for each parameter with a quote, plus feedback, a summary and up to three ideas.
3. `evidence.py` drops any item whose quote the teacher never said (or wrote, for a confirmed photo), and any wording that breaks the rules.
4. `delivery.score()` scores voice and camera from the signal bins.
5. Code turns levels and measurements into points per parameter, 0–100 per card and an overall score. The LLM never sets a score directly.
6. The report is validated against `ReportOut` before it is returned.

---

## 4. Every AI file, what it does

### 4.1 `backend/app/services/`

| File | What it does | Public functions | Things to tune |
|---|---|---|---|
| `llm.py` | The only code that calls an LLM. Asks for JSON matching a Pydantic class, retries once on a bad reply. If the Gemini model is busy (503, 429, timeout) it tries the next Gemini model, resting a failed one for 120 s; OpenAI only if a key is set. Can send images with the prompt, and can try a named model first. | `generate_json(prompt, Schema, system="", timeout_s=60, images=(), model=None)`, `is_fake()`, `LLMError` | `GEMINI_FALLBACK_MODELS`, `TIMEOUT_S`, `REST_S` |
| `stt.py` | The only code that calls speech-to-text. Sends Whisper an example of punctuated Indonesian classroom speech so it writes question marks, drops silence and Whisper's stock hallucinations. | `transcribe(wav_bytes, language="id")` → text or `""`; `STTError` | `NO_SPEECH_THRESHOLD`, `STYLE_PROMPT` |
| `questions.py` | The AI students. Decides when a student speaks (plain code) and what they say (Gemini, with canned fallbacks). Depth level 1–3 per grade, one misconception question per lesson from the teacher's book, answers to the teacher's own questions, a "satisfied" reaction or one follow-up, a capstone, nudges. | `next_event(db, session_id, now_ms)`, `capstone(db, session_id)`, `to_event(question_row)` | `DEMO_INTERVAL_MS` (75 s), `SILENCE_NUDGE_MS`, `ANSWER_GAP_MS`, `LLM_TIMEOUT_S` |
| `rag.py` | The teacher's material as text. Splits each PDF page into paragraph chunks; a photo's reading is stored as the chunks of its page. Finds the text on screen and the chunks closest to what is being said (shared rare words; not embeddings). | `index_material(db, material_id)`, `index_page(db, material_id, page, texts)`, `page_text(db, material_id, page)`, `closest_chunks(db, material_id, text, k, skip_page)` | `MAX_CHUNK_CHARS` |
| `examples.py` | Also `read_picture(db, file_id, subject)`: copies the text of a picture a teacher adds as material (`prompts/image_read.md`), stored as that item's page; nothing is checked. Photos of handwritten worked examples. Read (copy only), wait for the teacher to confirm or edit, then check on exactly that text. Reader sees the photo, checker never does. Fairness rules in code: no verdict on a skipped step, notes that judge are replaced. | `add`, `read`, `confirm`, `for_material`, `public` (signatures in section 5) | `MAX_SIDE_PX`, `STATUS_TEXT`, `.env` `LLM_VISION_MODEL` |
| `metrics.py` | Numbers from timestamps, no AI: words per minute on speaking time, pauses (gaps of 2 s or more), teacher questions (a "?" or a question opener), thinking time (3 s or more after a question), response time to students, fillers, time per slide, reading share (8 or more words in a row from the slide on screen). | `compute(db, session_id)` → `LessonMetrics` (`.public()` is the report's `metrics`) | `PAUSE_MS`, `THINKING_TIME_MS`, `READ_RUN`, `QUESTION_OPENERS` |
| `delivery.py` | The "Suara & ekspresi" card from the 10 s bins: lively voice, emphasis at key moments, reacting to a student, facial movement, gestures, posture. Moments count, not duration; smiles only add; dark bins are skipped. | `score(bins, asked, segments)` → (parameter fractions, liveliest moments) | `LIVELY_PITCH`, `LIVELY_FACE`, the `*_BAND` values |
| `scoring.py` | Builds the whole report (section 3.5). | `build_report(db, session_id)` → `Report` dict | `WPM_BAND` and the other `*_BAND` values, `MIN_WORDS`, `MAX_IDEAS` |
| `rubric.py` | The six cards, their parameters and points, as data. Growth labels, the target-band function, the subject's own Clarity parameters and practice list. | `CARDS`, `FREE_CARDS`, `growth_label`, `band`, `clarity_parameters`, `worked_practice` | card weights and parameter points |
| `evidence.py` | Honesty and kindness checks: a quote must be the teacher's own words (said, or written in a confirmed example); banned words; emotion words. | `find_quote`, `find_written`, `unnumbered`, `banned_words`, `emotion_words`, `unkind` | `BANNED`, `EMOTIONS` |
| `profiles.py` | Loads the subject profiles. | `get(profile_id)`, `list_tested(include_untested=False)` | — |
| `report_schema.py` | The `Report` as Pydantic classes. | `ReportOut` (use as `response_model`) | — |

### 4.2 `backend/app/prompts/` (text, in Bahasa Indonesia)

| File | Used by | Asks the model for |
|---|---|---|
| `question.md` | `questions.py` | One student question about what was just said, at an allowed depth level, about the slide or photo on screen |
| `misconception.md` | `questions.py` | A question built on a misconception from the teacher's book |
| `answer.md` | `questions.py` | A student's short answer to the teacher's question, or nothing if it was not really a question |
| `reaction.md` | `questions.py` | Whether the teacher's answer settled the question: an acknowledgement, or one polite follow-up |
| `capstone.md` | `questions.py` | The one closing question |
| `rubric.md` | `scoring.py` | Levels 1–5 with quotes, feedback (worked / noticed), feedback on each worked example, a summary, up to three ideas |
| `example_read.md` | `examples.py` | A copy of the photo's question, steps and final answer, never corrected, unsure parts marked |
| `example_check.md` | `examples.py` | Its own working, then a verdict per step: follows / recheck / cannot_tell, with a plain note |

### 4.3 `backend/app/profiles/`

`matematika-fase-e.yaml` (Matematika Kelas X, demo chapter Bab 7 Peluang). Every field is copied from the teacher's book with page numbers in comments; sources in `docs/rubric-sources.md`.

| Field | Changes |
|---|---|
| `label`, `student_persona` | How the AI students are described and how they talk |
| `question_types`, `question_depth`, `example_questions`, `assumed_knowledge` | What the students ask, how deep, and what they already know |
| `misconceptions` | Five documented misconceptions, each with trigger words and a fallback question |
| `clarity_parameters` | The two subject-specific parameters of the Kejelasan card |
| `worked_example_practice` | What a clearly set-out worked example looks like in this subject |
| `accuracy_focus`, `phase_expectation`, `context_seeds` | What "accurate" means here, what the grade is expected to reach, and contexts for ideas |
| `tested` | Shown in Setup only when true |

Adding a subject is a new YAML file, not code.

### 4.4 `frontend/src/features/simulator/vision/` (runs in the browser)

| File | What it does |
|---|---|
| `index.ts` | `startSignals({ stream, video?, now, onBin, onFrame?, onVoice? })` → `{ cameraOn, calibrate(), stop() }`. The only thing the room imports |
| `audioSignals.ts` | Loudness and pitch from the microphone (WebAudio, pitch by autocorrelation, spread in semitones) |
| `camera.ts` | MediaPipe Face and Pose Landmarker at about 5 fps; falls back to voice only if the models fail to load |
| `features.ts` | Per-frame features: facing the device, upright, hands moving, face moving away from the teacher's own neutral face. No eye contact, no emotion |
| `calibration.ts` | The 3 s baseline: neutral face, resting posture, resting voice |
| `binning.ts` | Averages into one `Bin` every 10 s; marks a bin "not measured" when too dark or the face is too small |
| `types.ts` | `Bin` exactly as in the contract |

Needs one package in the frontend: `npm install @mediapipe/tasks-vision@0.10.14`. Until `frontend/package.json` exists, the folder is typechecked, tested and tried from `ml/vision-harness/` (`npm install`, `npm run check`, `npm run dev` opens a page with live signals from a webcam, the microphone, or a recorded clip).

### 4.5 `ml/eval/`: try the AI with no frontend

Run from `backend/`. They use your `.env` keys and a throwaway in-memory database, so they never touch `app.db`.

| Command | Shows |
|---|---|
| `python ../ml/eval/check_providers.py [clip.wav]` | That Gemini (and Groq, with a clip) answer with your keys |
| `python ../ml/eval/try_questions.py` | A whole Peluang lesson played through the AI students: every event, its kind and level |
| `python ../ml/eval/try_report.py [lesson.txt] [--json] [--example photo.jpg]` | The full report for a lesson, and whether it passes the feedback rules |
| `python ../ml/eval/try_example.py photo.jpg [--confirm] [--model NAME]` | What was read from a photo; with `--confirm`, the check |

### 4.6 Tests: `backend/tests/`

110 tests, run with `cd backend && pytest`. They never call a provider, whatever is in your `.env`.

| File | Covers |
|---|---|
| `test_services.py` | LLM retry and fallback, STT cleaning, profiles, PDF chunking and retrieval |
| `test_questions.py` | When and what the AI students say: depth, misconception, answer, reaction, capstone, nudge |
| `test_metrics.py` | Every metric from fixed timestamps; reading share |
| `test_scoring.py` | The report shape, the evidence check, wording rules, the arithmetic, tiers, worked examples in the report |
| `test_delivery.py` | The Suara & ekspresi card from synthetic bins |
| `test_examples.py` | Reading, confirming and checking a photo, and its use in a lesson |

---

## 5. The functions your endpoints call

`db` is the SQLModel session from `app.core.db.get_session`. **A background task must open its own session** (`with Session(engine) as db:`), because the request's session is closed when the reply is sent.

| Function | Called from | Returns | Time |
|---|---|---|---|
| `stt.transcribe(wav_bytes)` | `POST /sessions/{id}/audio` | text, or `""` when there is no speech | 1–3 s |
| `questions.next_event(db, session_id, now_ms)` | the same, after saving the segment; `now_ms` = the chunk's `end_ms` | an `Event` dict or `None`; already saved | 0–6 s |
| `questions.capstone(db, session_id)` | `POST /sessions/{id}/end` | an `Event` dict; already saved | 2–12 s |
| `rag.index_material(db, material_id)` | `POST /materials`, after saving the file and the row | nothing | under 1 s |
| `examples.add(db, material_id, filename, path)` | `POST /materials/{id}/examples`, after saving the image | the `WorkedExample` row, `status: "reading"` | instant |
| `examples.read(db, example_id, subject="")` | the same, **in the background** | the row; never raises for a bad photo or a busy provider | 10–30 s |
| `examples.confirm(db, example_id, question=None, steps=None, final_answer=None, subject="")` | `POST /examples/{id}/confirm`; pass only the fields sent | the row with its check; `ValueError` when there is nothing to confirm (answer 400) | 5–15 s |
| `examples.for_material(db, material_id)` | `GET /materials/{id}/examples` | the rows in page order | instant |
| `examples.public(row)` | every endpoint returning an example | the contract's `Example` dict | instant |
| `scoring.build_report(db, session_id)` | `POST /sessions/{id}/finish`, **in the background** | the complete `Report` dict, validated | 10–40 s |
| `profiles.list_tested()` | `GET /profiles` | the profile list | instant |

Errors: `ValueError` for an unknown id (answer 404), `stt.STTError` and `llm.LLMError` when no provider answered (answer 502 for audio; mark the report as failed for `/finish`).

### 5.1 Two endpoint sketches

These are sketches to show the calls, not finished code; the endpoints are BE+FE 2's. `segment_dict` stands for your own schema conversion.

```python
# backend/app/api/audio.py
@router.post("/sessions/{session_id}/audio")
def upload_audio(session_id: str, seq: int = Form(...), start_ms: int = Form(...), end_ms: int = Form(...),
                 file: UploadFile = File(...), db: Session = Depends(get_session)):
    stored = db.exec(select(TranscriptSegment).where(TranscriptSegment.session_id == session_id,
                                                     TranscriptSegment.seq == seq)).first()
    if stored:  # a resent piece: answer again, but never transcribe or ask a second time
        return {"seq": seq, "segment": segment_dict(stored), "event": None}
    # (A silent piece saves no segment, so a resent silent piece is not caught above. Keep a small
    # set of seen seq numbers per session if that matters; it only risks a repeated nudge.)
    text = stt.transcribe(file.file.read())
    segment = None
    if text:
        segment = TranscriptSegment(session_id=session_id, seq=seq, start_ms=start_ms, end_ms=end_ms, text=text)
        db.add(segment)
        db.commit()
    event = questions.next_event(db, session_id, now_ms=end_ms)
    return {"seq": seq, "segment": segment_dict(segment) if segment else None, "event": event}
```

```python
# backend/app/api/sessions.py
def make_report(session_id: str) -> None:
    with Session(engine) as db:  # its own session: the request's one is already closed
        report = scoring.build_report(db, session_id)
        db.add(Report(session_id=session_id, data=report, overall_score=report["overall"]["score"]))
        db.commit()

@router.post("/sessions/{session_id}/finish", status_code=202)
def finish(session_id: str, background: BackgroundTasks):
    background.add_task(make_report, session_id)
    return {"report_status": "pending"}
```

A silent piece (no text) still goes to `next_event`: that is how a 30 s silence turns into a nudge. A resent piece must not create a second event.

---

## 6. Setup, keys and the database

### 6.1 Running it

```
cd backend
pip install -r requirements.txt
cp ../.env.example .env        # then fill it in, or set both providers to fake
uvicorn app.main:app --reload
pytest
```

### 6.2 `.env` settings the AI reads

| Setting | Meaning |
|---|---|
| `STT_PROVIDER` | `groq`, `openai` or `fake` |
| `LLM_PROVIDER` | `gemini`, `openai` or `fake` |
| `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY` | Keys. OpenAI is optional, used only as a last fallback |
| `STT_MODEL` | `whisper-large-v3` |
| `LLM_MODEL` | The Gemini model tried first, e.g. `gemini-3.8-flash` |
| `LLM_VISION_MODEL` | Optional: the model tried first for reading photos. `gemini-2.5-flash` read our test photo in about 8 s; the default model was busy and took about 30 s |

Never commit `.env`. Keys are shared privately.

### 6.3 Tables the AI added or uses

| Table | AI use |
|---|---|
| `material_chunks` | Filled by `rag`; the text of every PDF page and every photo page |
| `worked_examples` | **New.** One row per photo: `page`, `status`, `reading`, `check_result` (sent as `check` by `examples.public`) |
| `materials` | `filename` and `path` may now be empty (photos only, no PDF) |
| `questions` | Columns `level`, `reply_to`, `satisfied` added for question depth and the "satisfied" reaction |
| `transcript_segments`, `slide_events`, `signal_bins` | Written by your endpoints, read by the AI |
| `reports` | Written by your `/finish` task with the dict from `build_report` |

SQLite does not change an existing file. **Delete `backend/data/app.db` once after pulling**; it is recreated on startup.

### 6.4 Working without keys

With both providers set to `fake`:
- `stt.transcribe` returns sample Indonesian sentences in turn.
- The AI students use their canned lines.
- A photo comes back with a sample Peluang reading, one step marked unclear, and the check agrees after confirming.
- `build_report` returns a complete report whose texts start with "(Contoh)".

---

## 7. What was built, in order

| Milestone | When | What |
|---|---|---|
| M0 | 12 Oct | Branch, provider wrappers (`llm.py`, `stt.py`), question engine, material chunks, profiles; fixed the test that would not run |
| M1 | 12 Oct | `metrics.py` and `evidence.py`: every number from timestamps; quotes checked against the transcript; banned and emotion words |
| M2 | 12 Oct | The real report: six cards 0–100, named parameters with points, one Gemini call for levels and feedback, the evidence check, at most three ideas, `ReportOut` |
| M3 | 12 Oct | Questions by subject and grade (depth levels), misconception questions from the teacher's book (Bab 7 Peluang, five misconceptions with pages), LLM capstone; students answer the teacher's own question and show when an answer landed; question detection that does not need Whisper's "?"; sources for the scoring limits |
| M4 | 13 Oct | Voice and camera signals in the browser (`vision/`), the "Suara & ekspresi" card, the test harness in `ml/vision-harness/` |
| M7 step A | 13 Oct | Handwritten worked examples: image input in `llm.py`, `examples.py` (read, confirm, check), photo pages in `rag.py` and `metrics.py`, the reader-model setting |
| M7 step B | 13 Oct | Worked examples in the score and the report: two new parameters, feedback beside each example, written lines as evidence once confirmed, the practice list from the books, contract and grading docs |

Not done yet: M5 (evaluation numbers from real clips and sample lessons), M6 (the other five subject profiles), and the PRD update for worked examples.

---

## 8. Can the AI still change after you start building?

**Yes.** The AI lead will keep improving the AI after you start, for example making the grading parameters better or tuning thresholds, without breaking your code. The rule is simple: **the function signatures in section 5 and the shapes in `docs/api-contract.md` are fixed; everything behind them may change.**

Free to change, with nothing to do on your side:
- Prompts (`backend/app/prompts/*.md`): how students speak, what the rubric looks for.
- Points and weights (`rubric.py`), target bands and thresholds (`scoring.py`, `metrics.py`, `delivery.py`), parameter titles and descriptions.
- Profiles: new subjects, better misconception lists, a profile marked `tested`.
- Which Gemini model is used, retry and timeout behaviour.
- New parameters inside a card. The frontend already draws `dimensions[].parameters` as a list, so a new parameter appears on its own.

Needs a contract change and a message to the team first:
- Adding, renaming or removing a field in `Report`, `Event`, `Example` or `Bin`.
- A new event kind, a new endpoint, or a change to a function signature in section 5.
- A new table or column: everyone deletes `app.db` again.

How such a change is made: the contract is updated in the same commit as the code, the tests are run (`pytest`), and the team chat gets one line saying what changed. The AI lead never pushes a change that fails the tests, and never changes `api/`, `schemas/` or pages without asking their owner.

For the frontend this means: draw what the report gives you (titles, labels, texts and the parameter list), and do not hard-code parameter names, points or wording. Then a better rubric tomorrow shows up on your page with no change.

---

## 9. Known limits, so nobody is surprised

Full list with reasons: `docs/todo.md`, section 3. The ones you will notice while building:

- **The maths profile is `tested: false`,** so `GET /profiles` is empty unless you pass `include_untested=True`.
- **The camera code has not run on a real camera yet.** Voice-only works in the harness; open `ml/vision-harness` and try your webcam.
- **Handwriting reading has only been tried on printed stand-ins.**
- **Screen sharing mode B with a PDF also uploaded** makes the AI assume page 1 is on screen (section 3.4). Use `material_id: null` for mode B until `page: 0` is agreed.
- **Gemini's free tier is often busy (503).** The fallback handles it, but a reply can take 10–30 s. Background tasks for `read` and `build_report` are not optional.
- **Thresholds are provisional** until our labelled clips exist; scores are believable but not yet tuned.
- **Retrieval is shared-word matching, not embeddings.** Say "retrieval" in the pitch, not "embeddings".
