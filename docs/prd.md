# [BaSKom @ JOINTS] Product requirements

Version 2, Tue 13 Oct 2026. Replaces draft v1 of 28 Sep, which lives in the team's Google Doc ("PRD BaSKom @ Joints"). This version brings the PRD in line with what the team decided and built since then. Section 16 lists every change from v1.

The product name is not decided. Draft v1 used a working name; it is not carried over here, and no name goes into code, UI text or docs until the team picks one.

Where this file and another disagree: `docs/api-contract.md` wins on endpoints and JSON shapes, `docs/delivery-grading.md` on scoring, `CLAUDE.md` on product principles. `docs/todo.md` lists what is unproven.

## 1. What we are building

A rehearsal room for Indonesian teachers. A teacher presents their own material in a room that looks like a video call. AI students ask questions, answer the teacher's questions and show when an explanation has landed. Afterwards the teacher gets a report built from evidence in their own words: what worked, what we noticed, and up to three ready-to-use ideas.

It turns micro-teaching, a proven practice method, into something a teacher can do alone, at any time, on one modest laptop.

**Stance.** A rehearsal partner and a mirror, not a judge. Feedback is input the teacher may ignore.

## 2. Who it is for

- **Teachers across Indonesia**, mostly outside big cities, many with little money. One modest laptop; camera and shared material on the same screen.
- **Why they need it.** Teachers in well-resourced schools get coaching and observation; these teachers do not. The aim is equal access to practice, especially moving from reading slides to engaging lessons.
- **Their reality.** Low pay and heavy administrative load. The product saves time, never adds work, and never treats the teacher as the problem.

Proto-personas, carried over from v1 and still not validated with real teachers:

| Persona | Wants | In the product |
|---|---|---|
| Early-career teacher, Free tier | To rehearse a new topic and face unexpected questions before a full class. Easily overwhelmed by long reports | Short setup, kind feedback, at most three ideas |
| Mid-career SMA subject teacher, Free or Institutional | Sharper explanations, objective evidence on pacing and delivery | Uploads own slides, reads the parameter breakdown |
| School or institution, Institutional | Access for its teachers | Buys access and aggregate usage. Never sees an individual teacher's scores |

## 3. Product principles (never broken)

These override any requirement below.

- No eye-contact scoring. No emotion labels. Cheerful is not the goal; a calm, serious teacher can reach the top score.
- Lighting, camera quality and equipment are never scored.
- The camera is optional. A full report works from audio alone.
- Video never leaves the browser. Only small JSON signal bins and audio chunks are uploaded.
- Every qualitative point quotes the teacher's own words with a timestamp; a quote not found in the transcript is dropped.
- Feedback order: what worked, what we noticed, an idea you could try. At most three ideas. No "lacking", "poor", "weak", "should" (nor "kurang", "lemah", "seharusnya"). No comparison with other teachers, schools or countries.
- Ideas need no extra preparation time, materials or devices; the tool writes the example or story itself.
- Nothing in the product or pitch implies these teachers are low quality. The framing is unequal access to coaching.
- The teacher owns the data. No individual scores to principals.
- The rubric is "aligned with" the Kemendikdasmen guides, never "the official rubric".
- Local only. No deployment.

## 4. Status at a glance (13 Oct)

| Module | Owner | State |
|---|---|---|
| AI pipeline: speech-to-text, AI students, metrics, scoring, report | AI + PM | Built and tested on the backend (74 automated tests). Runs end to end from a typed lesson; not yet run with a person speaking |
| Voice and camera signals | AI + PM | Written, typechecked and unit-tested. Not yet run with a real camera or microphone |
| REST endpoints, login, storage | BE+FE 2 | Database tables exist. Endpoints not built |
| Simulator Room (audio capture, stage, room UI) | BE+FE 1 | Not built. The frontend project is not scaffolded |
| Report, History, Dashboard, Setup pages | BE+FE 2 | Not built |
| Landing page, design, pitch deck, video | UIUX | A History and report design exists in Figma; the state of the rest is not recorded here |
| Evaluation numbers | AI + PM | None yet. Needs recorded clips |
| Subject profiles | AI + PM | Matematika X is filled from its teacher's book. Others not started |

## 5. Scope

**Must be flawless:** Setup → Simulator Room → Report.
**Kept thin:** History, Dashboard, tier gating.
**Cut to a static list:** Schedule.
**Single static page:** Landing.

### Not in this build

- Spoken (text-to-speech) AI students. Chat text only; browser speech synthesis is a stretch item.
- PPTX upload. Teachers export to PDF first.
- Handwritten-note photo check (a "Should" in v1). Cut.
- Storing video or audio. Video never leaves the browser; audio is deleted after transcription.
- Calendar, reminders and deep links for Schedule.
- Peer comparison, leaderboards, PDF export, human coach review, an admin view of individual teachers.
- Student grade analytics.
- Real authentication, hosting, a mobile app.
- Training any model.

## 6. Simulator Room

**Owner:** BE+FE 1 for the room; AI + PM for the AI students and the signal code.

The room looks like a video call with screen share. The teacher's material is the main stage, their camera is a small tile, AI students are tiles beside it, and the transcript and student messages sit in a side panel. With the camera off the teacher's tile shows initials and everything else works the same.

### Features

| | Feature | Requirement |
|---|---|---|
| F1 | Setup | Choose a subject profile (subject and grade), class, chapter, sub-chapter. Optionally upload the chapter as a PDF (max 20 MB). A failed upload offers "continue without material" |
| F2 | Share material, like a video call | Two ways to put material on the stage, described below: present a PDF inside the app, or share a screen or window. Without material the stage shows the lesson topic |
| F3 | Live audio | Microphone required. The browser cuts audio at silences and sends each piece as a numbered request; the reply carries the transcribed text. A repeated number is ignored, so a retry after a network drop is safe |
| F4 | AI students ask | After enough teaching (60–90 s of speech in demo mode, 4 minutes otherwise) one student asks one question about what was just said and the slide on screen. No repeats |
| F5 | Depth by grade | Each question has a level: 1 clarify, 2 why or how, 3 what-if. The subject profile sets which levels a grade may use; grade X starts at 1–2 and allows one level 3 per lesson; a grade XI profile is meant to start at 2 |
| F6 | Misconception question | Once per lesson, when the teacher reaches a topic with a misconception documented in the teacher's book, a student asks a question built on it |
| F7 | Students answer the teacher | When the teacher ends on a question to the class, one student answers it, sometimes only partly right, so the teacher has something to build on. "Paham ya?" gets no answer |
| F8 | Satisfied signal | After the teacher answers a student's question, that student shows a gesture and a short acknowledgement, and the teacher carries on. If the answer did not address the question the student asks one follow-up; after that they are always satisfied. No new question is asked while one is open |
| F9 | Nudge | After 30 s of silence, one quiet line of text. No question is generated from silence |
| F10 | Capstone | "Selesai mengajar" produces exactly one closing question. After the answer the session closes and the report starts |
| F11 | Voice signals | Loudness and pitch from the microphone, in the browser, every 10 seconds. Works with the camera off |
| F12 | Camera signals (optional) | Pretrained face and body landmarks in the browser, after a 3-second calibration to the teacher's own neutral position: facing the device, posture, hand movement, and how far the face moved from neutral. Dark or unreadable stretches are marked "not measured" |
| F13 | Live HUD | Small framing and pace indicators, so the signal work is visible in the first seconds of the demo |
| F14 | Demo mode | A 5–7 minute configuration with the short question interval |

What a student may never do: assess the teacher, name an emotion, or address the teacher as "Pak" or "Bu" (the tool does not know).

### Sharing material (F2)

The teacher shares what they teach from, the way they would in a video call. Two modes; the teacher picks one in the room and can switch.

| | Present a PDF in the app | Share screen or window |
|---|---|---|
| How | Upload the chapter as a PDF in Setup; it is rendered on the stage with next/previous and arrow keys | The browser's own screen-share picker ("Bagikan layar"), as in Zoom or Meet: a whole screen, a window or a tab |
| Good for | Slides and chapters that exist as a PDF. Teachers with PowerPoint export to PDF first | PowerPoint with animations, a website, a simulation, any app |
| What leaves the browser | The PDF, once, at upload | Nothing. The shared picture is shown on the stage only; it is never uploaded, recorded or analysed |
| What the tool knows | The text of the page on screen and the time of every page turn | Only what the teacher says |
| AI student questions | About what was just said and the slide on screen | About what was just said. If a PDF was also uploaded, the backend currently assumes page 1 is showing; until the team agrees that the room sends `page: 0` for the shared screen, start a screen-share session without a PDF (`docs/ai-pipeline.md`, section 3.4) |
| Report | "Own words versus reading" and time per slide are measured | Those two parameters are unavailable and give their points to the rest of their cards. Nothing is lost from the score |

- Presenting a PDF is the recommended mode, because it is what lets the tool tell explaining from reading, and it costs almost nothing on a weak laptop.
- Screen sharing needs no backend endpoint. It is a browser feature (`getDisplayMedia`) shown in the stage area.
- The "video never leaves the browser" principle covers the shared screen as well as the camera.
- State: neither mode is built yet (BE+FE 1). Screen sharing was added to this PRD on 13 Oct; `docs/plan.md` still describes the PDF mode only.

### Acceptance criteria

| Criterion | State |
|---|---|
| The teacher picks profile, class, chapter and sub-chapter and lands in the room with that context | Not built (frontend) |
| A valid PDF is split per page and used for questions and scoring; an invalid or oversized file shows an error and the teacher can continue without it | Splitting and lookup built and tested; upload endpoint not built |
| The teacher can share a screen or window on the stage; the network tab shows no screen frames uploaded; stopping the share returns the stage to the PDF or the topic | Not built (frontend) |
| Denying the camera keeps the session running on audio; denying the microphone blocks the start with a clear message | Signal code falls back to voice only; room not built |
| Spoken Bahasa Indonesia appears as timestamped text; word error rate measured on 3 or more recordings with different accents | Transcription wrapper built; not measured |
| In demo mode a relevant question appears at least every 90 s of continuous speech, with no duplicates | Built and tested |
| At least 2 student questions in a 7-minute session; reviewers rate 80% of 10 sampled questions relevant | Not measured |
| Each question carries a depth level allowed for its grade | Built and tested |
| One misconception question per lesson, taken from the profile's list, about the topic being taught | Built and tested for Matematika X (five misconceptions, with page numbers) |
| A student answers a real question to the class and stays silent on a rhetorical one | Built and tested; run once on a typed lesson |
| Every student question gets a reaction; a follow-up is always followed by a satisfied reaction | Built and tested |
| "Selesai mengajar" triggers exactly one closing question | Built and tested |
| Signals are stored as 10-second bins; the browser's network tab shows no video frames | Bin code built; not verified in a browser |
| A 10-second network drop or a page refresh loses no transcript already captured | Backend ignores repeats; client retry not built |
| Three consecutive 7-minute sessions finish on the demo laptop without a restart | Not run |
| A first-time user reaches the live room in under 2 minutes | Not measured |

## 7. Report

**Owner:** AI + PM for scoring; BE+FE 2 for the page.

One object holds everything; the frontend computes nothing. Shape: `Report` in `docs/api-contract.md`.

### What the teacher sees, top to bottom

1. **Opening.** Two or three warm sentences naming the best moment of this lesson, and the overall score out of 100 with a growth label: *Mulai tumbuh* (below 50), *Berkembang* (50–79), *Kuat* (80 and up).
2. **Yang sudah berjalan baik.** Two or three strengths, each with the teacher's own words and a timestamp.
3. **Six cards.** Score, growth label, the parameters behind the score, one "what worked" and one "what we noticed".
4. **Saat paling hidup.** Up to four moments where voice or face came alive, by timestamp.
5. **Pertanyaan murid.** Every exchange with a student: the question and its depth level, the teacher's answer quoted, response time, whether the student was satisfied, any follow-up; and each time a student answered the teacher.
6. **Angka.** Words per minute, pauses, questions asked, thinking time, share read from the slide, time per slide.
7. **Ide yang bisa dicoba.** At most three, each tied to a moment in this lesson, with the finished text to say in class.
8. Every item has an "Ini tidak akurat" button; a flagged item is hidden from then on.

### The six cards

Each card is 100 points split over named parameters. Full table and arithmetic: `docs/delivery-grading.md`.

| Card | Weight in overall | Scored by | Needs |
|---|---|---|---|
| Ketepatan materi (accuracy) | 20 | LLM, against the teacher's own material | Transcript, PDF if uploaded |
| Alur mengajar (teaching flow) | 15 | LLM | Transcript |
| Kejelasan (clarity) | 20 | LLM; two of four parameters come from the subject profile | Transcript |
| Keterlibatan murid (engagement) | 25 | LLM and computed | Transcript, PDF for "own words" |
| Tempo (pacing) | 10 | Computed | Transcript timestamps |
| Suara & ekspresi (tone and expression) | 10 | Computed from signal bins | Voice signals; camera optional |

### How a score is made

- **Numbers first.** Pace, pauses, questions asked, thinking time, response time, reading share and time per slide are computed in code. The LLM never estimates them.
- **One LLM call** gives a level of 1–5 per parameter with a quote, plus draft feedback and ideas. The output is validated against a schema; an invalid reply is sent back once.
- **Evidence check.** A feedback item whose quote is not in the transcript is dropped. A level of 4 or 5 without a real quote falls to 3.
- **Wording check.** Feedback containing a banned word or an emotion word is dropped; a summary that breaks the rule is replaced.
- **Arithmetic in code.** Levels become points; computed parameters use a target band (full marks anywhere inside a comfortable range). The LLM never sets a card score.
- **Missing inputs never cost points.** A parameter that could not be measured (no PDF, no student question, camera off) gives its points to the rest of its card. A card that cannot be measured is "unavailable" and leaves the overall score untouched.

### Tone and expression

The aim is to tell a lively delivery from a flat one without asking for non-stop cheerfulness.

- **Moments, not duration.** Credit comes from voice and face coming alive at the greeting, at a question to the class, and when answering a student.
- **Smiles only ever add.** A smile counts as a warm moment; not smiling is never a deduction while face and voice are alive in other ways. Raised brows on a serious face count the same as a smile.
- **Measured against the teacher's own baseline**, so a quiet voice or a serious face is not marked down.
- **Described, never labelled.** "Pada 00:05 suara dan wajah Anda hidup saat menyapa murid", never an emotion word.
- Tone is measured from the audio signal (pitch and loudness). Speech-to-text produces only words.

### Acceptance criteria

| Criterion | State |
|---|---|
| A finished session produces a report with an overall score and all six cards; cards outside the plan are visibly locked | Built and tested |
| Every qualitative item shows the teacher's own words and a timestamp; a quote absent from the transcript is never shown | Built and tested |
| Pacing figures come from timestamps, not from the LLM | Built and tested |
| At most three ideas, each with ready-to-use text | Built and tested |
| The report opens with a strength | Built and tested |
| No banned word and no emotion label reaches the teacher | Built and tested |
| With no signal bins the report still generates and marks Suara & ekspresi unavailable; with the camera off the card is scored from voice | Built and tested |
| Invalid model output is retried once; a final failure returns a clear error, never a blank report | Built and tested; the friendly retry screen is frontend, not built |
| A recording under about 40 words gets a short notice and no score | Built and tested |
| The report is saved once per session and opens identically from History | Report builder done; storage endpoint not built |
| Report ready within about 60 s of the session ending | 9–36 s in four runs on a typed lesson, depending on which model answered |
| A deliberately weak lesson scores lower than a strong one on at least 4 of 5 scored cards | Not run; sample lessons not written |
| Scoring the same session twice differs by 10 points or less per card | Not measured; three early runs of one lesson gave 56, 58 and 63 overall |
| Suggestions rated useful, 4 of 5 or better, by at least 2 real teachers | Not done |
| "Latih topik ini lagi" opens Setup with class, subject and chapter filled in | Not built (frontend) |

## 8. Subject profiles

One engine, one data file per subject and grade. Cards, weights, the 0–100 scale and the feedback rules are identical for every profile.

| Comes from the profile | Example for Matematika X |
|---|---|
| Two Clarity parameters | "Explains why the rule works", "more than one representation" |
| What accuracy focuses on | Each step of a calculation and its result |
| What the phase expects | Capaian Pembelajaran Fase E for the chapter |
| What students already know | Simple probability from SMP |
| Kinds of question, depth ladder | Levels 1–2 first, one level 3 per lesson |
| Sparking questions as examples | Three, copied from the teacher's book |
| Documented misconceptions | Five for Bab 7 Peluang, with page numbers |
| Contexts for suggested examples | Daily life, financial literacy, climate, health |
| Student persona | Age 15–16, everyday language |

Target scope is six profiles: grade X Matematika and Bahasa Inggris; grade XI Matematika Tingkat Lanjut, Bahasa Inggris, Sejarah, Biologi. Tingkat Lanjut is included to show the difference between teaching maths and advanced maths.

Rules:
- A profile is offered in Setup only once it has its source book and a strong and a weak sample lesson that pass the discriminative check. Until then it is hidden and shown on the roadmap slide.
- Misconceptions are copied from the teacher's book with page numbers, never invented. A chapter whose book lists none ships without misconception questions.
- Vocabulary difficulty is never scored against a grade list. One parameter applies at every grade: new terms are explained when first used.

State: Matematika X is filled (demo chapter Bab 7 Peluang) but not yet marked tested. Teacher's and student books for Matematika Tingkat Lanjut XI, Biologi XI and Sejarah XI are on hand, unread. No English books yet.

## 9. History, Dashboard, Schedule, Landing

**Owner:** BE+FE 2 (History, Dashboard, Schedule); UIUX (Landing). None built yet.

### History (thin)
- Newest-first list of sessions with date, subject, chapter and the overall score out of 100 with its growth label.
- Opening an entry shows exactly the report first generated; it is stored whole.
- A trend arrow per card once two or more earlier sessions exist; hidden otherwise.
- Empty state points to starting a session. A session without a report shows as incomplete, not as a broken link.
- Design note: the Figma's "Areas to improve" block is "Yang kami perhatikan" (plain observations with a timestamp), "AI Suggestions" is "Ide yang bisa dicoba", every "What went well" bullet carries a quote, and Quick Highlights shows six cards, not four. The sidebar's "Student's grades" page has no data behind it and is not in scope.

### Dashboard (thin)
- "Mulai Sesi" is the dominant element and reaches Setup in one tap.
- The last one to three sessions with their scores; an empty state for a new teacher.
- Plan label (Free or Institutional).

### Schedule (static)
- A static list of planned practice sessions. No calendar, reminders or deep links in this build.

### Landing (one static page)
- What it is and who it is for; supported subjects and grades stated plainly; one call to action into the app.
- Reads cleanly on a phone. No placeholder text.

## 10. Plans

| | Free | Institutional |
|---|---|---|
| Cards | Ketepatan materi, Alur mengajar, Kejelasan, Keterlibatan murid | Adds Tempo and Suara & ekspresi |
| Price | Free for individual teachers | IDR 100,000 per user per month (proposed in the preliminary paper; not yet benchmarked) |

- One feature flag, not two code paths. A locked card returns no score and no parameters, and is shown with a visible lock.
- Keterlibatan murid is in Free because it is the core of the mission. v1 had only accuracy and flow (plus clarity) in Free; **the team has not confirmed this change.**
- The Institutional plan sells access and aggregate usage. It never gives a principal an individual teacher's scores.

## 11. Data and privacy

- **Stays in the browser:** every video frame, every landmark, raw audio samples used for pitch and loudness.
- **Uploaded:** short audio pieces for transcription, deleted afterwards; 10-second signal bins (nine numbers each); page-turn times; the teacher's PDF.
- **Stored locally in one SQLite file:** users, materials and their text, sessions, transcript, student events, signal bins, the report as JSON, and "not accurate" flags.
- **Sent to hosted AI services:** audio pieces to the speech-to-text provider, and transcript text with the relevant slide text to the LLM provider. The app runs locally, but these two calls leave the laptop.
- The camera models (about 10 MB) are downloaded from a public CDN on first use.
- The teacher can flag any feedback item as not accurate. Deleting a session from History is recommended and not yet specified.

## 12. Architecture

Short version; details in `docs/architecture.md` and `docs/plan.md`.

| Layer | Choice |
|---|---|
| Frontend | React, Vite, TypeScript, Tailwind, on `localhost:5173` |
| Backend | FastAPI, Python 3.11+, on `localhost:8000` |
| Database | One SQLite file via SQLModel, created on startup |
| Speech-to-text | Groq-hosted `whisper-large-v3`, prompted with punctuated Indonesian classroom speech |
| LLM | Gemini Flash with JSON output. When the configured model is busy the next Gemini model is tried, and a failing model is skipped for two minutes |
| Material lookup | PyMuPDF splits the PDF per page; the chunks closest to what is being said are found by weighted word overlap |
| Voice signals | Web Audio in the browser: loudness, and pitch by autocorrelation |
| Camera signals | `@mediapipe/tasks-vision` Face and Pose Landmarker, in the browser, about 5 frames a second, dropping to 2 on a slow device |

- Plain REST. All AI calls go through one speech-to-text function and one LLM function; the provider is chosen in `.env`, and `fake` runs with no key and no network.
- Every LLM step has a fallback: a canned question, a satisfied student, or a clear error for the report.
- OpenAI is supported in code as a fallback provider, but the team is not using it and no key is set.

Differences from `docs/architecture.md` as it stands today, to be reconciled there: it says the camera models run in a web worker (they run on the main thread) and that material lookup uses embeddings (it uses word overlap).

## 13. Success metrics and evaluation

Nothing here is measured yet. Each table in `docs/evaluation.md` is filled by a script, never by hand.

| Metric | Target | State |
|---|---|---|
| Speech-to-text word error rate | Reported per clip, 3 or more Indonesian clips with different accents | Needs clips |
| Question relevance | 80% of 10 sampled questions rated relevant | Not run |
| Teacher-question detection | Detected versus hand-counted on our clips | Not run |
| Strong versus weak lesson | Weak lower on at least 4 of 5 scored cards, per profile | Needs sample lessons |
| Re-score consistency | 10 points or less per card on the same lesson | Not run |
| Signal agreement | Per signal, against hand labels on held-out clips | Needs paired flat and lively clips |
| Time to report | About 60 s | 9–36 s on a typed lesson |
| Stability | Three 7-minute sessions without a restart | Needs the room |
| Real teachers | At least 2 rate the suggestions | Not done |

Where the scoring limits come from: thinking time of 3 s rests on Rowe's wait-time research (1986); the speaking-rate band is adapted from English lecture studies; the rest are our own starting values, to be tuned on labelled clips and never presented as research findings. Sources: `docs/todo.md`.

## 14. Business and viability

Not an app feature: the commercial and impact case for the pitch. Carried over from v1; the numbers are proposals from the preliminary paper, not results.

- **Model.** Free for individual teachers; Institutional at IDR 100,000 per user per month. Present the price as proposed until benchmarked against comparable Indonesian pricing.
- **Year 1 target.** 1,500 educators (1,000 Jabodetabek, 500 other regions), from the preliminary roadmap. Note the tension with section 2: the product is designed for teachers outside big cities, so the go-to-market should say how it reaches them.
- **Go-to-market.** Name specific schools or teacher communities (KKG, MGMP) the team can realistically reach. Still open.
- **Positioning.** Extra practice between sessions with mentors and peer groups, for teachers who have no coach nearby. It complements people.
- **Impact claims.** Hattie's (2009) micro-teaching effect size of 0.88 describes the method the product is built on, not the product's own result; check which population it refers to before repeating it. "25–40% competency improvement" and "60% faster feedback" are targets or benchmarks from other contexts, never achieved results. Nothing is deployed.
- **Cost.** One sentence in the deck on running the Free tier at Year 1 scale: speech-to-text minutes and LLM calls per session. The free tiers used for the demo are not a cost model.
- **Evidence.** If no real teacher has seen it before submission, the deck says so plainly.

Acceptance: every number in the deck's business section has a source or is marked "team assumption".

## 15. Timeline, deliverables, risks, open decisions

### Timeline
| Date | Goal |
|---|---|
| Tue 13 Oct | Feature freeze at noon. Polish, bug fixing, rehearsals |
| Wed 14 Oct | Record the 2-minute video; finish the deck with evaluation tables; README |
| Thu 15 Oct | Submit |
| Fri 16 Oct, 23:59 WIB | Deadline. Buffer only |
| 23 Oct | Announcement |
| 1 Nov | Grand Final, FMIPA UGM |

The freeze has passed with the room, the endpoints and every page still to build. See risks.

### Submission deliverables (JOINTS guidebook)
- Demo video: YouTube, public, at most 2 minutes. Mandatory.
- Source code: GitHub repository. Mandatory.
- Pitch deck: PDF. Mandatory.
- Prototype or mockup: UI/UX mockup and interactive prototype. Mandatory.
- Proposal: PDF, at most 10 pages. Optional.

Eligibility and disqualification rules in the guidebook have still not been reviewed.

### JOINTS rubric
Technical Implementation 30%, Solution Innovation 25%, Functionality & Design 20%, Impact & Implementation Feasibility 15%, Presentation & Demo 10%. The lever is a visibly real AI pipeline with measured numbers, not more pages.

### Top risks
| Risk | Mitigation |
|---|---|
| No room, endpoints or pages two days before submission | Build only Setup → Room → Report. The backend functions are ready to be called, and run with fake providers and no keys. The report and the student conversation can be shown from the command line today |
| The free-tier LLM is busy on demo day | Two fallback models; canned questions and a satisfied student if all fail. Record the video early |
| Camera signals unverified | Fallback from the plan: run the same code on the recorded video after the session and call it post-session delivery analysis. The report is complete from audio alone |
| Scores vary between runs | Pin one model for scoring, or score twice and average, if the consistency check fails |
| No evaluation numbers for the deck | Record the clips first; an honest "not yet measured" beats an invented number |
| Overclaiming impact | Every figure is a target or a benchmark with its source |

### Open decisions
| Decision | Who |
|---|---|
| The product name | Team |
| Keterlibatan murid in the Free plan | Team |
| Scores out of 100 and the "Suara & ekspresi" card, agreed by the lead on 12 Oct | Team to confirm |
| Whether a late student answer is shown or dropped in the room | BE+FE 1 |
| Demo chapters for Matematika Tingkat Lanjut XI, Biologi XI, Sejarah XI | AI + PM |
| Whether a teacher can delete a session | Team |
| A named Year 1 go-to-market | Team |
| Agree `docs/api-contract.md` (still marked draft) | Team |

## 16. What changed from draft v1 (28 Sep)

| Area | Draft v1 | Now | Why |
|---|---|---|---|
| Product name | A working name throughout | None until the team decides | Team decision pending |
| Stance | Scored feedback report | A rehearsal partner and mirror; feedback the teacher may ignore | The tool has no authority on pedagogy |
| Eye contact | Gaze toward the camera as an eye-contact proxy | Not measured at all | Camera and shared material are on the same screen, so looking at the camera and reading the slide cannot be told apart, and neither is wrong |
| Expression | Smile versus neutral proxy | Movement from the teacher's own neutral face; a smile only ever adds; no emotion named | Cheerful is not the goal |
| Lighting, camera quality | Not addressed | Never scored; dark stretches are "not measured" | They reflect what a teacher can afford |
| Score scale | 1–5 per dimension | 0–100 per card, with named parameters and points. Each parameter is still judged 1–5 internally | Matches the design; shows where a score comes from |
| Dimensions | Content accuracy, Teaching flow, Clarity, Pacing, Tone & engagement, On-camera presence | Accuracy, Teaching flow, Clarity, Engagement, Pacing, Tone & expression | Engagement is the headline; voice moved to delivery; the last card works with the camera off |
| Feedback | "What went well", "What to improve", Top 3 actions | What worked, what we noticed, at most three ideas with ready-to-use text; banned words; no comparisons | Kind, and no extra work for the teacher |
| Free plan | Accuracy, flow (clarity suggested) | Adds Engagement | Core of the mission. Not yet confirmed |
| AI students | One student; clarification, example, misconception probe | Three named students; questions by depth level per grade; one documented misconception per lesson; students answer the teacher; a satisfied signal with at most one follow-up | Back-and-forth discussion; difference between grades made visible |
| Capstone | "Advanced, out-of-the-box" question to test mastery | One closing question that ties the lesson together | Not a test of the teacher |
| Subjects | One curriculum, two subjects | One profile per subject and grade, as data files; six targeted | Teaching maths is not teaching history |
| Rubric basis | Anchored descriptors | Aligned with the ministry's subject guide and teacher's books, with page numbers | The rubric comes from people, not the model |
| Material | PDF, optional PPTX; screen share as a "Should" | Two modes: a PDF presented inside the app with page turns logged (recommended), or a shared screen or window that stays in the browser | With the PDF the app can read the slide on screen; screen sharing covers everything a PDF cannot |
| Reading versus explaining | Not present | "Own words" parameter: share of speech read from the slide on screen | The mission is moving from reading slides to engaging lessons |
| Speech-to-text | Local Whisper or Gemini audio, undecided | Groq-hosted Whisper large v3 | Free, fast, good on accents; local is too slow |
| Transport | Streaming, WebRTC mentioned | Plain numbered requests | Simpler to build and debug |
| Material lookup | Embeddings | Weighted word overlap | Enough for one PDF per session |
| Camera analysis | "On-device", 2–5 frames a second | Same, on the main thread, with a 3-second calibration | A web worker is not built |
| Hosting | Hosting and cost ceiling open | Local only, no deployment | Nothing to host |
| Handwritten-note check | Should | Cut | Time |
| Schedule | Calendar, reminders, deep links; owned by Business+BE | A static list | Paid for the subject profiles |
| Team roles | AI+PM, FE+BE, Business+BE, UI/UX | AI+PM, BE+FE 1, BE+FE 2, UIUX | As the team now works |
| Coach or principal | Reads a teacher's report | Never sees an individual's scores | It must not become a surveillance tool |
| Copy | A branded label for the AI student | Named students; no product name in UI text | Name undecided |
| Milestones | Feature-complete 11 Oct | Backend AI pipeline complete 13 Oct; room and pages not started | See status |

## 17. References

- JOINTS UGM 2026 Hackathon Guidebook: rubric, timeline, deliverables.
- BaSKom preliminary paper, Ristek Hackathon 2026, and its score breakdown.
- *Panduan Mata Pelajaran Matematika, Fase A–F* (BSKAP Kemendikdasmen, 2025).
- *Buku Panduan Guru Matematika SMA/MA/SMK/MAK Kelas X*, Edisi Revisi (Kemendikbudristek, 2023). Page references: `docs/rubric-sources.md`.
- Rowe, "Wait Time: Slowing Down May Be a Way of Speeding Up!", *Journal of Teacher Education* 37(1), 1986.
- Hattie (2009); McKinsey Global Institute (2023); Aipilot (2025); World Population Review (2025); Baharuddin & Burhan (2025): as cited in the preliminary paper, each a benchmark or motivation, not this product's result.
- In this repo: `docs/plan.md`, `docs/api-contract.md`, `docs/delivery-grading.md`, `docs/rubric-sources.md`, `docs/architecture.md`, `docs/todo.md`, `docs/evaluation.md`.
