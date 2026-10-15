# [BaSKom @ JOINTS] AI teaching simulator — build plan, 9–15 Oct

Working name is `[BaSKom @ JOINTS]`; the product name is not decided, so no product name appears in code, UI text or CLAUDE.md until the team picks one. The UI reads the name from a single constant so it can be changed in one place.

## Context

The product lets Indonesian teachers rehearse a lesson: AI students ask questions live, and the teacher gets an evidence-linked report (content, flow, clarity, pacing, tone, on-camera delivery). The PRD is solid on product and acceptance criteria but names no stack, and nothing is built yet. Today is Fri 9 Oct; submission is Thu 15 Oct. That is 6 days from zero for 4 people, so the plan optimises for one flawless end-to-end demo flow over module count.

JOINTS weights: Technical 30%, Innovation 25%, Functionality & Design 20%, Impact 15%, Demo 10%. The winning lever is a visibly real AI pipeline with measured numbers, not more pages.

## Project context (carried into CLAUDE.md)

- **Who it is for:** teachers across Indonesia, most of them outside big cities and many with little money. They teach from one device, usually a modest laptop, with the camera and the shared material on the same screen, like a video call.
- **Why it exists:** teachers in well-resourced schools get coaching and observation; these teachers do not. The goal is to give them the same chance to practise and improve, especially at making lessons engaging instead of reading from slides.
- **Their reality:** low pay and heavy administrative load. The product must save time, never add work, and never treat them as the problem.
- **Stance:** a rehearsal partner and mirror, not a judge. Feedback is input the teacher is free to ignore.
- **Consequences for the build:** audio-first, camera optional, light on bandwidth and hardware, Bahasa Indonesia with regional accents, no eye-contact or emotion scoring, evidence quoted from the teacher's own words.

## Two things to clear up first

**Accents and slang are a speech-to-text problem, not a vision problem.** Face and body landmarks are language-independent, so the pretrained landmark approach is unaffected by how someone speaks. What it is sensitive to is lighting, camera angle, glasses, hijab and distance from the camera; we handle that with a 3-second per-user calibration and test it on our own clips. Accent robustness is decided by the STT model choice below.

**The $20 OpenAI credit is usable and is plenty as a fallback.** Whisper-class transcription costs about $0.006/min, so $20 covers tens of hours. Plan is free-first, with OpenAI only as the safety net on demo day.

## Architecture

```
Browser (React, localhost)                   FastAPI (localhost)         SQLite file
 ├─ mic → 16 kHz PCM → WAV chunks at pauses ──POST /audio──► STT ──► transcript segments ─► app.db
 ├─ camera → MediaPipe (web worker, ~5 fps)                 ├─ question engine (LLM + RAG)
 │    → features → 10 s bins (JSON only) ──POST /signals──► ├─ metrics (pure Python)
 └─ room UI: transcript, AI student, HUD   ◄── events ───── └─ scoring (LLM → JSON schema → evidence check)
```

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Vite + TypeScript + Tailwind, on `localhost:5173` | Team's stack |
| Backend | FastAPI (Python 3.11), on `localhost:8000` | Python for the AI pipeline |
| DB + auth | SQLite file via SQLModel; one simple local login, no real auth | Zero setup, nothing to host |
| STT | Groq-hosted `whisper-large-v3` (free tier), OpenAI transcription as fallback | Best multilingual accent coverage at zero cost; local Whisper is too slow on free CPU hosts |
| LLM | Gemini Flash (free tier) with structured JSON output; OpenAI small model as fallback | Free, fast, good Indonesian |
| RAG | PyMuPDF → chunks → embeddings stored per session, cosine in NumPy | One PDF per session; no vector DB needed |
| Vision | `@mediapipe/tasks-vision` Face Landmarker (blendshapes + head matrix) and Pose Landmarker, in the browser | On-device, no training, privacy claim is verifiable in the network tab |

**Local only, no deployment.** Everyone runs frontend and backend on their own laptop with their own `.env` keys; the demo video is recorded from one laptop. "Local" means the app runs locally; it still calls hosted AI services for speech-to-text and the LLM, because running those models on a laptop is too slow.

**How the browser talks to the backend, in plain terms.** While the teacher talks, the browser cuts the audio into short pieces (a few seconds each, cut at natural pauses) and sends each piece to the backend as an ordinary web request. The backend turns that piece into text and replies with it. If it is time for a student question, the same reply also contains the question. Each piece is numbered, so if one is sent twice by accident the backend ignores the repeat. This is the simplest way to get a live transcript; the alternative (a permanently open connection) is harder to build and debug.

**Swappable AI providers.** The backend has exactly one function that does speech-to-text and one that calls the LLM. Everything else calls those two. If a free tier runs out mid-week, we change one line in `.env` to switch provider (for example to the OpenAI credit) and no other code changes. Free-tier limits must be checked on day 1 with real keys.

**What the RAG is for.** RAG means "look things up in the teacher's own material before asking the AI". The teacher uploads the chapter PDF. We split it into paragraphs. During the lesson we find the few paragraphs closest to what the teacher is currently saying and paste them into the prompt. That does two jobs: (1) AI students ask about the actual chapter instead of generic questions, and (2) Content accuracy is scored against the chapter, so the model cannot mark a correct statement wrong from its own shaky memory. With no PDF, both steps fall back to the transcript alone.

## The Simulator Room looks like a video call with screen share

The teacher uploads their material when entering the room and presents it there, the way they would share a screen on Zoom.

- **Layout:** the material is the main stage. The teacher's camera is a small tile, AI students are tiles beside it, and the live transcript and student questions sit in a side panel. With the camera off, the teacher tile shows their initials and everything else works the same.
- **Presenting:** the uploaded file is rendered inside the app (pdf.js) with next/previous page controls and arrow keys. This is not real screen capture, which matters: because the app holds the file, it can read the text of the page being shown, and it costs almost nothing on a weak laptop.
- **Every page turn is logged with a timestamp.** That gives three things for free: AI student questions are about the slide currently on screen; "own words vs reading" compares what was said against the text of that exact slide; and time spent per slide appears in the report.
- **File types:** PDF for the MVP. Teachers with PowerPoint export to PDF first (one sentence of guidance on the upload box); direct PPTX support is a stretch item.
- **No material:** the room still works; the stage shows the lesson topic and questions come from the transcript alone.

## Delivery analysis (the computer-vision part)

No model training. Pretrained landmarks plus our own feature layer, which is where the engineering credit comes from.

1. **Calibration (3 s, "look at the camera, sit how you teach")** stores baseline head pose, shoulder width and shoulder-to-nose height. Every feature is measured relative to this baseline.
2. **Per-frame features (~5 fps, web worker)**
   - Facing the class: head yaw/pitch from the face transformation matrix, used only to detect being turned well away from the device or out of frame. Eye contact is not measured: the teacher's camera and their shared material are on the same screen, so "looking at the camera" and "reading the slide" are indistinguishable and neither is wrong.
   - Setup quality: face size, centring and brightness, used only for an optional pre-session tip and to decide when signals are too unreliable to measure. Never part of any score.
   - Posture: shoulder-line tilt, slouch (shoulder-to-nose height vs baseline), lean, centred in frame.
   - Gestures: wrist speed normalised by shoulder width, hands in frame, gesture rate; flags "static" and "fidgeting".
   - Expression: smile and brow blendshapes reported as expressiveness (variation over time), never as an emotion label.
3. **Aggregation** into 10 s bins: `{t, facing_pct, posture_ok_pct, gesture_rate, expressiveness, face_visible_pct}`. Only this JSON is uploaded.
4. **Voice signals, same pipeline**: volume (RMS) and pitch variation from WebAudio for the Tone dimension; words per minute, pauses and question response time from transcript timestamps; Indonesian filler count ("eee", "anu", "apa ya", "gitu") with the caveat that Whisper drops some fillers.
5. **Evaluation, which is what makes it credible**: record 12–16 short clips across the 4 of us (bright/dim light, glasses, hijab, laptop vs phone camera, facing the device vs turned away, in and out of frame, slouched vs upright, an older low-spec laptop), hand-label each 10 s bin, report agreement per signal. Tune thresholds on half, report on the other half. Same idea for STT: word error rate on 3+ Indonesian clips with different accents. These tables go in the pitch deck and README.

### How delivery is graded (cheerful is not the goal)

Nothing is scored as "more is better", and no emotion is ever named or rewarded. A calm, serious teacher must be able to score 5.

| Signal | What earns a good score | What lowers it | Never penalised |
|---|---|---|---|
| In frame | Being in the picture for most of the lesson | Only long stretches fully out of frame | Lighting, camera quality, background, room; reading the shared material; where the eyes point |
| Posture | Stable, upright, in frame | Sustained slouch or drifting out of frame | Moving around |
| Gestures | Some hand movement while explaining | None at all for minutes, or constant repetitive fidgeting | Style or size of gestures |
| Expression | Face is not frozen: it changes at meaningful moments, especially when a student asks a question | Several minutes with no facial movement at all | Not smiling; neutral or serious face |
| Voice | Pitch and volume vary; pace in a comfortable range | Monotone for long stretches; much too fast or slow | Low energy, accent, dialect |

Rules that keep this fair:
- **Target bands, not maximums.** Each signal has an acceptable range; inside it the score is full. Only extremes cost points.
- **Responsiveness over positivity.** The one expression measure with real teaching meaning is whether the teacher visibly reacts when a student asks something (turns to camera, nods, brow movement). We measure the 5 s after each AI question.
- **Weights.** On-camera presence = responsiveness to student questions 40%, gestures 25%, posture 15%, expression variation 10%, in frame 10%.
- **Lighting and equipment are never scored.** Brightness and camera quality reflect what a teacher can afford, not how they teach. They appear only as an optional friendly tip before the session ("facing a window may help students see you"). If the picture is too dark for the landmarks to be reliable, those stretches are marked "not measured" and left out of the score rather than counted against the teacher.
- **Shown as evidence, not judgement.** The report says "from 03:10 to 04:40 you were out of frame", with the timestamp, not "you seemed unengaged".
- **Camera is optional and never required for a full report.** The core feedback (content, flow, clarity, pacing, handling questions) comes from audio alone. On a weak device the vision model drops to 2 fps with the lite models, or switches off, and On-camera presence is marked unavailable without lowering the overall score.
- **Bands are set from our labelled clips**, and ideally checked with one or two real teachers; the deck states plainly that these are delivery signals, not a measure of teaching quality on their own.

A live HUD in the room (small framing and pace indicators) makes the vision work visible within the first 10 seconds of the demo video.

Fallback if live analysis is unstable by Sun 11 Oct: run the same code on the recorded video after the session, in the browser, labelled "post-session delivery analysis".

## Engagement: the headline dimension

The mission is helping teachers move from reading the slides to making the lesson interesting: stories, examples, applying ideas to students' lives, inviting students in. This is measured almost entirely from the transcript, so it works with audio only on any device.

| Parameter | What we look for | How it is measured |
|---|---|---|
| Own words vs reading | Explaining the material rather than reading it out | Computed: share of the teacher's speech that is near word-for-word from the uploaded material (shared word sequences). Only long sustained stretches count; reading a definition is normal. Unavailable without a PDF. |
| Examples and application | Concrete examples, analogies, links to daily life or local context | LLM finds each one and must quote it; count and timestamps shown |
| Story and hook | An opening that creates curiosity; a short story or case | LLM, quoted; first 60–90 s checked for a hook |
| Inviting students in | Asking questions, checking understanding, giving thinking time | Computed: questions the teacher asks, and the pause after each (3 s or more counts as thinking time) |
| Building on student questions | Answering the AI student directly and extending it with an example | LLM on the answer text, plus computed response time |
| Voice variation | Emphasis and change of pace at key points | Computed pitch and volume variation (from the delivery signals) |

**How the feedback is written (inputs, not judgement).** Every item has three parts:
1. *What worked*, always first, with a quote: "At 02:15 you compared voltage to water pressure in a pipe. That kind of comparison is what students remember."
2. *What we noticed*, as a plain observation with a timestamp: "From 04:00 to 06:30 the explanation followed the slide text closely."
3. *An idea you could try*, ready to use and specific to this chapter: the tool writes the story opener, everyday example or question for them, in Bahasa Indonesia, using context the teacher's students would recognise.

**Rules that respect the teacher's reality.** Many of these teachers are underpaid and buried in administrative work; reading from slides is usually a symptom of no preparation time, not of not caring.
- Suggestions must need no extra preparation time, materials or devices. The tool does the preparation by generating the example or story itself, so it saves time instead of adding a task.
- At most three ideas per report. No lists of shortcomings.
- No comparison with other teachers, schools or countries. No words like "lacking", "poor", "weak", "should". Wording is "you could try", "one idea".
- Nothing in the product or the pitch states or implies that these teachers are low quality. The framing is unequal access to coaching, not unequal teachers.
- Scores carry a growth label next to the number (for example "starting", "developing", "strong") and the report opens with strengths.

**Changes to the PRD rubric this implies, for the team to confirm:** "Tone & engagement" becomes "Engagement" as defined above, with voice tone moved under delivery signals; and Engagement sits in the Free tier, since it is the core of the mission.

## Rubric anchored in the official teaching guide

Source: *Panduan Mata Pelajaran Matematika, Fase A–F* (BSKAP Kemendikdasmen, 2025), section D "Perencanaan Pembelajaran Mendalam". Read so far: introduction, subject characteristics, section D and its first example plan; section C (220 pages of per-topic notes) was only sampled.

What it is and is not: a guide for planning lessons, written about what students experience. It contains no instrument for scoring a teacher. So our rubric is "aligned with" it, never "the official rubric", and the deck says so.

| In the guide | Becomes in our rubric |
|---|---|
| Three principles: *berkesadaran, bermakna, menggembirakan* | The three sub-headings of Engagement, in the guide's own words |
| *Berkesadaran*: students know the learning goal | New parameter "Purpose": the goal is said aloud early (LLM, quoted) |
| *Memahami* characteristic: link new to prior knowledge | New parameter "Linking back": a reference to what students already know (LLM, quoted) |
| *Bermakna*: apply knowledge in real personal/local/national/global context | Anchors for "Examples and application" |
| *Pertanyaan pemantik* (sparking questions) | "Story and hook" renamed "Hook" and anchored on this term |
| *Menggembirakan* = a positive, challenging, motivating atmosphere | Confirms our rule: it is about curiosity and challenge, not a cheerful face |
| Lesson sequence *memahami → mengaplikasi → merefleksi* | Anchors for Teaching flow: is there an apply moment, and a reflective close? |
| Five process elements (reasoning and proof, problem solving, communication, representation, connection) | Maths-specific Clarity anchors: explains why not only the formula; uses more than one representation |
| Context list: local wisdom, financial literacy, climate, health | Seed list for "an idea you could try", so suggestions use contexts the ministry itself recommends |
| Example reflective questions and sparking questions | Few-shot examples in the suggestion prompt |
| Plans must adapt to available resources, "with or without technology", and local economic conditions | Official backing for the no-extra-materials rule |

Second source: *Buku Panduan Guru Matematika SD/MI Kelas IV* (Pusat Perbukuan, 2022). Read: contents, general strategy, one full sub-chapter, a sample of the misconception notes. Every sub-chapter has the same blocks, and three of them are directly usable:

| Block in the teacher's book | Use |
|---|---|
| *Pengalaman belajar* ("the teacher explains what students will be able to do") | Confirms the "Purpose" parameter |
| *Apersepsi* and *Pertanyaan pemantik* | Confirms "Linking back" and "Hook"; the listed questions are few-shot examples |
| *Miskonsepsi* (25 documented student misconceptions, e.g. adding from the leftmost digit) | AI students voice the documented misconception for the topic being taught, and the report notes how the teacher handled it. This is the strongest new feature from the sources. |
| "This activity may be replaced to fit what is around your students" | Backs local-context suggestions |

The two sources are different editions of the curriculum (2022 Kurikulum Merdeka, 2025 Pembelajaran Mendalam). The framework comes from the 2025 guide; the 2022 book is used for topic content and misconceptions only. It is a grade 4 book, so it does not cover the grade 10–11 scope below.

## One rubric, one profile per subject and grade

The team is considering grade 10 (maths, English) and grade 11 (maths, English, history, biology). The dimensions, the 1–5 scale and the feedback rules stay identical for all of them. What changes is a small profile file per subject and phase (grade 10 = Fase E, grade 11 = Fase F):

| Stays the same | Comes from the profile |
|---|---|
| Six dimensions and their weights | Clarity anchors (maths: reasoning and representations; other subjects: from their own guide) |
| All computed metrics (pace, pauses, reading overlap, questions asked) | Context seeds for suggested examples |
| Feedback format and wording rules | Misconceptions the AI students can voice |
| Evidence check | AI student persona: age and how a student of that grade asks |

- **Word choice is not scored against a grade-level vocabulary list.** No trustworthy Indonesian readability measure exists for this. Instead one parameter applies at every grade: "new terms are explained when first used" (LLM, quoted). The grade shows up through the AI students: a grade 10 student asks when a term was not explained.
- Grade 10 and 11 differ little; the real difference is between subjects. English lessons add a speech-to-text check for mixed Indonesian and English speech.
- A profile is offered in the UI only once it has its source guide and a strong and weak sample transcript.

**Decided scope: all six** (grade 10 maths, English; grade 11 maths, English, history, biology), with **misconception questions as a core feature**. To make that fit in six days:
- Profiles are data files, never code. One mechanism is built once (Sat 10) with grade 10 maths; the other five are added as files on Mon 12.
- One demo chapter per profile, not the whole year. The misconception list covers that chapter only.
- Needed from the team by Sun 11: the *Panduan Mata Pelajaran* for English, history and biology, and the grade 10/11 *Buku Panduan Guru* chapter for each of the six demo chapters. A profile without its documents is not shipped.
- Each profile gets one strong and one weak sample transcript (12 in total, about 3 minutes each, written by the team and split four ways).
- Paid for by dropping the Schedule module to a static list, and keeping History and Dashboard at their thinnest.
- If Tue 13 noon arrives with a profile untested, it is hidden in the UI and shown on the roadmap slide instead. Maths grade 10 is the recorded demo either way.

Limits we keep:
- Many example activities are hands-on or group work (tangram sets, pair discussion). A solo rehearsal cannot show these, so their absence is never scored.
- This guide covers maths only. The demo uses a maths lesson; the Clarity anchors are stored per subject so other subjects can be added. Whether other subject guides share section D is to be checked, not assumed.
- The PDF is 59 MB: kept in `docs/references/` and git-ignored; the extracted anchors live in `docs/rubric-sources.md` with page numbers.
- Stretch only: index section C so AI students and Content accuracy can use the per-topic notes.

## What gives the AI standing to give feedback

It has none as an authority on pedagogy, so the product is built as a rehearsal partner and a mirror, not a judge:
- **The rubric comes from people, not the model.** Anchored descriptors are adapted from the Kemendikdasmen subject guide (see the section above), with page references. A published teacher-observation instrument is still to be found and cited alongside it. The LLM applies them; it does not invent criteria.
- **Facts are computed, opinions are quoted.** Pace, pauses and response times are measurements. Every qualitative point must quote the teacher's own words with a timestamp, so the teacher can check it and disagree.
- **Content accuracy is judged against the teacher's own material**, not the model's memory.
- **The teacher has the last word.** Each feedback item has a "this is not accurate" button; flagged items are hidden and logged. Wording is "something to try next time", never a verdict.
- **The teacher owns the data.** Reports are private to the teacher. The Institutional tier sells access and aggregate usage, not individual scores to a principal, so it cannot become a surveillance tool.
- **It complements people.** Positioned as extra practice between sessions with mentors and peer groups (KKG/MGMP), for teachers who have no coach nearby.
- **Checked with real teachers.** At least 2 teachers rate the suggestions before submission; their ratings and criticisms go in the deck.

## AI pipeline

- **Questions**: every 60–90 s of speech in demo mode, send the last transcript window, the text of the slide currently on screen plus the closest other material chunks, and the list of questions already asked; the model returns one question with a student persona and the transcript moment it refers to. Once per session, when the teacher reaches a topic with a documented misconception in the profile, one AI student asks a question built on it (stored with kind `misconception`); the report quotes how the teacher responded. Duplicate check by embedding similarity. Silence over 30 s returns a nudge. "Selesai mengajar" triggers one capstone question, then close.
- **Report**: metrics computed in Python first; the LLM scores Content accuracy, Teaching flow, Clarity and the quoted parts of Engagement on 1–5 anchored rubrics and must return quotes; Pydantic validates, one retry on failure; every quote is string-matched against the transcript and dropped if absent. Pacing and On-camera presence are scored from the computed metrics by rule, not by the LLM. Temperature 0 for the ≤0.5 consistency target.
- **Stretch**: AI students speak via the browser's built-in `id-ID` speech synthesis.

## Scope

Must be flawless: Setup → Simulator Room → Report. Keep thin: History (list + reopen report + trend arrow), Dashboard (start button, last sessions), tier gating (one flag, locked cards). Cut: Schedule is a static list of planned sessions, to pay for the six subject profiles. Landing page is a single static page.

## Folder structure (first thing to create on approval)

```
speach/
├─ README.md               setup, architecture diagram, evaluation numbers
├─ CLAUDE.md               project rules for Claude (see below)
├─ .claude/
│  ├─ settings.json        blocks git push, turns off Claude commit attribution
│  └─ agents/              project agents (see below)
├─ .gitignore  .env.example
├─ docs/
│  ├─ prd.md               full PRD text, pasted in by you (my read of the Google Doc was a summary)
│  ├─ api-contract.md      endpoints + JSON shapes; agreed day 1, the team's source of truth
│  ├─ architecture.md
│  ├─ plan.md              this plan, copied in full
│  ├─ delivery-grading.md  delivery and engagement grading rules
│  ├─ rubric-sources.md    anchors taken from the teaching guide, with page numbers
│  ├─ references/          source PDFs (git-ignored, large)
│  ├─ evaluation.md        STT and delivery-signal results
│  └─ pitch/               deck, video script
├─ design/                 UIUX: exported assets, tokens, Figma link
├─ frontend/               BE+FE 1 and 2
│  └─ src/
│     ├─ pages/            Landing, Dashboard, Setup, Room, Report, History, Schedule
│     ├─ components/       shared UI
│     ├─ features/
│     │  ├─ simulator/
│     │  │  ├─ audio/      capture, pause detection, WAV encode, upload queue
│     │  │  ├─ vision/     MediaPipe worker, features, calibration, binning   (AI lead)
│     │  │  ├─ stage/      material viewer (pdf.js), page controls, page-turn logging
│     │  │  └─ room/       call layout, camera tile, AI student tiles, transcript panel, HUD
│     │  ├─ report/  history/  schedule/
│     ├─ lib/              api client, types copied from the contract, APP_NAME constant
│     └─ styles/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/              sessions.py, audio.py, signals.py, reports.py, materials.py, schedule.py
│  │  ├─ core/             config, auth, db
│  │  ├─ schemas/          Pydantic models (mirror api-contract.md)
│  │  ├─ services/
│  │  │  ├─ stt.py  llm.py                 provider wrappers with fallback
│  │  │  ├─ rag.py  questions.py           (AI lead)
│  │  │  ├─ metrics.py  scoring.py  evidence.py   (AI lead)
│  │  ├─ prompts/          question, capstone, rubric prompts as files
│  │  └─ profiles/         one file per subject and phase: anchors, context seeds, misconceptions, persona
│  ├─ tests/               metrics, evidence check, schema validation
│  ├─ requirements.txt
│  └─ data/                app.db (SQLite, git-ignored), uploaded PDFs
└─ ml/                     AI lead
   ├─ eval/                labelled clips manifest, STT WER script, signal agreement script
   ├─ notebooks/           threshold tuning
   └─ samples/             strong and weak lesson transcripts for the discriminative test
```

## Database

One SQLite file (`backend/data/app.db`), defined as SQLModel classes and created automatically on backend startup. Each laptop has its own copy; data is not shared between teammates. All ids are UUIDs. Moving to Postgres later is a connection-string change.

| Table | One row is | Key columns |
|---|---|---|
| `users` | a teacher | name, email, tier (free / institutional) |
| `materials` | an uploaded PDF | user_id, filename, file path on disk |
| `material_chunks` | one paragraph of a PDF | material_id, page number, order, text, embedding (stored as JSON) |
| `slide_events` | one page turn during a lesson | session_id, page number, t_ms |
| `sessions` | one practice lesson | user_id, class, subject, chapter, sub-chapter, material_id (optional), status (active / ended / partial), started_at, ended_at, camera_on, demo_mode |
| `transcript_segments` | one transcribed audio piece | session_id, seq, start_ms, end_ms, text; unique on (session_id, seq) so a resent piece is ignored |
| `questions` | one AI student question or nudge | session_id, kind (regular / misconception / capstone / nudge), persona, text, asked_at_ms, answered_at_ms, transcript moment it refers to |
| `signal_bins` | 10 seconds of delivery signals | session_id, t_start_ms, facing_pct, posture_ok_pct, gesture_rate, expressiveness, face_visible_pct, volume, pitch_variation; unique on (session_id, t_start_ms) |
| `reports` | the feedback report for a session | session_id (unique), full report as JSON, overall score, created_at |
| `feedback_flags` | a "this is not accurate" click | report_id, feedback item id, created_at |
| `schedule` | a planned practice | user_id, date and time, subject, chapter, session_id once started |

Everything hangs off `sessions`: a session has many transcript segments, questions and signal bins, and exactly one report. The report is stored whole as JSON so reopening it from History shows exactly what was first generated. Not stored: video (never leaves the browser) and audio (deleted after transcription).

## CLAUDE.md, settings and agents

**CLAUDE.md** is loaded into every Claude session in this repo, for every teammate, so it holds everything decided in this plan. To keep it readable it is split in two:
- `CLAUDE.md` itself (about one screen): what the project is and who it is for, the stack and run commands, the folder ownership map, the current day's goal, the hard rules below, and the product principles that must never be broken (no eye-contact scoring, no emotion labels, camera optional, evidence-quoted feedback, teacher owns the data, local only).
- Long context pulled in by import lines (`@docs/plan.md`, `@docs/architecture.md`, `@docs/delivery-grading.md`, `@docs/api-contract.md`): the full schedule, architecture, grading table and weights, the "AI standing" principles, and the contract. `docs/plan.md` is this plan, copied in full.

Hard rules in CLAUDE.md:
- Claude must never run `git push` or any command that writes to GitHub (no `gh pr create`, no remote changes). Humans push.
- Claude must never appear as a collaborator or author: no `Co-Authored-By` line, no "Generated with Claude Code" line, no Claude name or email in commits or PR text.
- Claude does not commit unless explicitly asked.

CLAUDE.md is guidance, so the same rules are also enforced in `.claude/settings.json`: a deny rule on `git push` and on `gh` write commands, and commit attribution switched off. That way a push is blocked even if an instruction is missed.

**Agents.** Yes, project agents can be created as files in `.claude/agents/`, and the whole team gets them through the repo. Three, kept small:
- `pm`: reads the PRD and schedule, reports what is done against acceptance criteria, and drafts each person's tasks for the day.
- `contract-check`: compares frontend calls and backend endpoints against `docs/api-contract.md` and lists mismatches. Run before merging.
- `ai-eval`: runs the scoring and signal evaluation scripts and summarises regressions.

**Plugins.** Claude Code has its own plugin system (`/plugin` in the chat opens the marketplace browser), and you install them yourself from there. It is a separate catalogue from claude.ai's, so I will not name specific plugins without you checking what is listed; the three agents above cover the PM and SWE help without any install.

This folder is inside OneDrive. Syncing `node_modules` and `.venv` there is slow and causes file locks; either move the repo outside OneDrive or exclude those folders before installing dependencies.

## How the team works in the repo

This plan file lives in one person's Claude folder, outside the project, so teammates cannot see it. On approval it is copied into the repo as `docs/plan.md`, and everything teammates need lives in the repo as plain Markdown that reads fine without Claude.

- **Sharing:** the AI+PM lead creates a private GitHub repo, pushes the scaffold themselves (Claude does not push), and invites the three teammates as collaborators. Each teammate clones it to their own laptop, outside OneDrive.
- **What each person reads first:** `README.md` (how to run it), `docs/plan.md` (what and when), `docs/api-contract.md` (the agreement between frontend and backend), and for UIUX `docs/delivery-grading.md` and the room layout section.
- **Not shared through git:** `.env` with API keys (each person copies `.env.example` and fills in their own, or the lead sends keys privately) and the local database file.
- **Branches:** `main` always runs. Each person works on a short branch named `name/feature`, opens a pull request, and merges at least once a day so branches never drift far. Folder ownership keeps people out of each other's files.
- **The contract comes first:** any change to an endpoint or JSON shape is made in `docs/api-contract.md` in the same pull request, and announced in the team chat.
- **Daily rhythm:** a 10-minute check-in each morning; the lead updates the "today's goal" line in CLAUDE.md and the checklist in `docs/plan.md`.
- **Teammates who use Claude Code** get `CLAUDE.md`, the push block and the agents automatically from the repo. Those who do not lose nothing.

## Who does what

| Person | Owns |
|---|---|
| AI + PM (you) | `frontend/.../vision/`, `backend/app/services/` AI files, `prompts/`, `ml/`, evaluation numbers, daily integration check |
| BE+FE 1 | Simulator Room: audio capture and upload queue, room UI, HUD, session lifecycle and resilience |
| BE+FE 2 | Database models, all REST endpoints, Report / History / Dashboard / Setup pages, one-command local run |
| UIUX | Figma for Room and Report first, design tokens, landing page, pitch deck, demo video |

## Schedule

| Day | Goal |
|---|---|
| Fri 9 | Scaffold repo, CLAUDE.md and settings, write `api-contract.md`, database models, everyone runs it locally. Spikes: STT on 3 Indonesian clips, MediaPipe running in a worker. Confirm free-tier quotas. |
| Sat 10 | Room works end to end: speak → transcript → AI question. Vision features and calibration. PDF upload and retrieval. Profile mechanism with grade 10 maths. |
| Sun 11 | Report: metrics, scoring, evidence check, report page. Signals saved with the session. Go/no-go on live delivery analysis. Subject documents for the other five profiles handed in. |
| Mon 12 | Five remaining profiles and their sample transcripts. History, Dashboard, tier gating, capstone, resilience. Record and label evaluation clips. |
| Tue 13 | Feature freeze at noon. Polish, landing page, bug fixing, three clean 7-minute rehearsals. |
| Wed 14 | Record the 2-minute video, finish deck with evaluation tables, README. |
| Thu 15 | Submit by midday. 16 Oct is emergency buffer only. |

## Verification

- `pytest backend/tests`: metrics from fixed timestamps, evidence check drops a fabricated quote, invalid LLM JSON triggers exactly one retry.
- `ml/eval`: WER per clip and per-signal agreement tables regenerate from one command each.
- `git push` attempted by Claude is blocked by `.claude/settings.json`; a test commit carries no Claude attribution.
- Manual run on a clean laptop following only the README: three consecutive 7-minute sessions without a crash, at least 2 relevant questions each, report in about 60 s.
- Browser network tab during a session shows only audio chunks and small JSON, no video frames.
- Deny camera → session continues audio-only and the report marks On-camera presence unavailable. Deny mic → blocked with a clear message.
- Throttle to offline for 10 s mid-session → no transcript lost.
- Engagement: a transcript read straight from the PDF scores high on "reading" and one in the teacher's own words scores low; a report containing a banned word ("kurang", "lemah", "seharusnya" and the English equivalents) fails a test; every report has at most three ideas and opens with a strength.
- Profiles: each of the six loads, produces a misconception question taken from its own list, and passes the strong-vs-weak check below; an untested profile does not appear in the Setup screen.
- Score the strong and weak sample lessons: weak is lower on at least 4 of 5 dimensions; scoring twice differs by at most 0.5.
