# API contract (DRAFT — to be agreed by the team on Fri 9 Oct)

Base URL `http://localhost:8000/api`. JSON unless stated. Ids are UUID strings. Times inside a session are milliseconds from session start (`*_ms`). Errors: `{ "detail": "message" }` with a 4xx/5xx status.

No real auth: after login the frontend sends `X-User-Id: <user id>` on every request.
A missing or unknown `X-User-Id` gives 401. A session or report that belongs to another user gives 404, as if it did not exist.
`GET /health`, `POST /auth/login` and `GET /profiles` need no header. Invalid fields give 422.

## Users

`POST /auth/login` — `{ name, email }` → `{ id, name, email, tier }` (`tier`: `free` | `institutional`). Creates the user if new.
- The email is stored lower-case; logging in again with the same email returns the same user.

## Profiles

`GET /profiles` → `[{ id, subject, grade, phase, label }]`. Only tested profiles are returned (`SHOW_UNTESTED_PROFILES=true` in `backend/.env` lists all of them, for local development).

## Materials

`POST /materials` — multipart, field `file` (PDF, max 20 MB), optional → `{ id, filename | null, page_count }`
- 400 if not a PDF; 413 if too large.
- Without a file an empty material is created (`page_count` 0). Setup always creates a material, so photos of worked examples have somewhere to live even when there is no PDF.

`GET /materials/{id}/file` → the PDF (for pdf.js). 404 when the material has no PDF.

### Handwritten worked examples ("Papan tulis")

A teacher can photograph a question and their own handwritten working. Each photo is an extra page of the material, numbered after the PDF's last page, and is shown on the main stage like a slide.

`POST /materials/{id}/examples` — multipart, field `file` (JPG or PNG, max 8 MB) → 202 `Example` with `status: "reading"`
- Call `examples.add()`, then `examples.read()` in the background. Allowed before the lesson and during it.
- 400 if not a JPG or PNG; 413 if too large.

`GET /materials/{id}/examples` → `[Example]`, in page order. Poll every few seconds while any `status` is `reading`.

`GET /examples/{id}/file` → the image.

`POST /examples/{id}/confirm` — `{}` or `{ question?, steps?: [text], final_answer? }` → `Example` with its `check`
- `{}` means "yes, this is what I wrote". Any field sent replaces that part, so a teacher can fix one number or type the whole example (also for a photo that could not be read).
- Calls `examples.confirm()`. This is the only place the working is checked. It may be called again after a further edit.
- 400 when there is nothing to confirm (no reading and no text sent).

`Example`: `{ id, material_id, page, status, status_text, reading | null, check | null }`

```
status:   reading | unconfirmed | confirmed | unreadable | failed
reading:  { question, steps: [{ n, text, unclear }], final_answer, answer_unclear }
check:    { answer, our_answer, steps: [{ n, status, note }], summary }
          // answer and each step's status: follows | recheck | cannot_tell
```

| `status` | Meaning | What to show |
|---|---|---|
| `reading` | The photo is being read (about 10–30 s) | The photo, usable on stage already |
| `unconfirmed` | Read; waiting for the teacher | "Apakah ini yang Anda tulis?" with `reading` in editable fields; parts with `unclear: true` highlighted. No check exists yet |
| `confirmed` | The teacher confirmed or edited | `check`: `summary`, and `note` on each step with `status: "recheck"` |
| `unreadable` / `failed` | Could not be read | `status_text`; the photo still works on stage, and the teacher may type the text and confirm |

- **Nothing about whether the working is right is computed or sent before the teacher confirms.** `check` is null until then.
- `status_text` and `check.summary` are ready-to-display Bahasa Indonesia. Wording is "layak dicek ulang", never "salah".
- During a lesson the confirmation is one tap on a small card that does not interrupt. An example the teacher never confirms is still shown and still used by the AI students, but is not checked and not scored.
- `page` is what to send to `POST /sessions/{id}/slides` when the photo is put on stage.

## Sessions

`POST /sessions` — `{ profile_id, class_name, subject, chapter, sub_chapter, material_id | null, camera_on, demo_mode }` → `Session`
- 422 for an unknown `profile_id` or an empty `class_name`, `subject` or `chapter`; 404 if `material_id` is not the user's.

`Session`: `{ id, status, started_at, ended_at | null, profile_id, class_name, subject, chapter, sub_chapter, material_id, camera_on, demo_mode }` (`status`: `active` | `ended` | `partial`)

`GET /sessions` → `[Session + { overall_score | null, overall_label | null }]`, newest first (History, Dashboard). `overall_score` is 0–100; both come from the stored report's `overall`.

`GET /sessions/{id}` → `Session`

### Audio

`POST /sessions/{id}/audio` — multipart: `seq` (int, from 0), `start_ms`, `end_ms`, `file` (WAV, 16 kHz mono)

→ `{ seq, segment: { seq, start_ms, end_ms, text } | null, event: Event | null }`

- Idempotent on `(session, seq)`: a repeated `seq` returns the stored result and does nothing else.
- `segment` is null when the chunk had no speech.
- Cut chunks at silence. `start_ms` and `end_ms` mark where speech starts and stops, not where a fixed-length chunk begins and ends: pauses and thinking time in the report are the gaps between chunks.

`Event`: `{ id, kind, persona: { name, style } | null, text, asked_at_ms, refers_to_ms | null, level | null, question_id | null, satisfied | null }`

At most one event per audio reply. What the room does with each `kind`:

| `kind` | Who speaks | Meaning | Room shows |
|---|---|---|---|
| `regular` | AI student | A question about what was just said. `level` 1–3 is its depth (1 clarify, 2 why/how, 3 what-if) | The question on that student's tile |
| `misconception` | AI student | A question built on a misconception documented in the teacher's book. Once per lesson | Same as `regular` |
| `answer` | AI student | The teacher ended on a question to the class; one student answers it. `refers_to_ms` is the teacher's question | The answer on that student's tile |
| `reaction` | The student who asked | Sent after the teacher has answered. `question_id` is the question it reacts to. `satisfied: true`: `text` is a short acknowledgement, show a gesture (nod, thumbs-up) and the teacher carries on. `satisfied: false`: `text` is one follow-up question | Gesture, or the follow-up |
| `capstone` | AI student | The one closing question, from `/end` | The question |
| `nudge` | Nobody (`persona` is null) | The teacher has been silent for 30 s | A quiet line of text |

- A student's question stays open until its `reaction` arrives; no other question is asked meanwhile.
- A follow-up (`satisfied: false`) is always followed by a `reaction` with `satisfied: true`, so a teacher is never stuck.
- An `answer` is written while the teacher pauses (2–6 s). If the teacher has already started speaking again when it arrives, the room may show it quietly or drop it.
- `level`, `question_id` and `satisfied` are null for the kinds that do not use them.

### Slides

`POST /sessions/{id}/slides` — `{ page, t_ms }` → 204. Sent on every page turn, and once for page 1 at start.
- A `page` above the PDF's `page_count` is a photo of a worked example (`Example.page`). Send it when the teacher switches the stage to that photo, and the PDF page again when they switch back.

### Signals

`POST /sessions/{id}/signals` — `{ bins: [Bin] }` → 204. Idempotent on `(session, t_start_ms)`.

`Bin`: `{ t_start_ms, facing_pct, posture_ok_pct, gesture_rate, expressiveness, face_visible_pct, volume, pitch_variation, measured }`
- One bin per 10 seconds, produced by `startSignals()` in `frontend/src/features/simulator/vision/`; the room only forwards them.
- `facing_pct`, `posture_ok_pct`, `face_visible_pct` and `gesture_rate` are shares of the bin, 0–1. `expressiveness` is how far the face moved from the teacher's own neutral face, 0–1. `volume` is average loudness, 0–1. `pitch_variation` is the spread of the voice's pitch in semitones, null when nobody spoke.
- `measured: false` when the picture was too dark or the face too small to trust; the camera values are then null and the bin is left out of camera scoring. Its voice values still count.
- With the camera off only `t_start_ms`, `volume`, `pitch_variation` are sent, with `measured: true`; the rest are null.

### Ending

`POST /sessions/{id}/end` → `{ event: Event }` — "Selesai mengajar": returns exactly one capstone question. Pressing it again returns the same question; 409 after `/finish`.

`POST /sessions/{id}/finish` → 202 `{ report_status: "pending" }` — after the capstone answer; starts report generation.
- Safe to call again: if the report exists or is being made, nothing new starts; if generation failed, it starts over. One report per session.

## Reports

`GET /sessions/{id}/report` → 200 `Report`, or 202 `{ report_status: "pending" }`, or 500 `{ detail }` if generation failed.
- 404 when `/finish` was never called for this session (or the backend restarted while the report was being made): call `/finish` again.
- The stored report is returned unchanged except that flagged items are left out of `strengths`, `ideas` and each dimension's `items`.

`Report` holds everything the scoring produces. The frontend computes nothing; `title`, `label_text`, `summary` and every `text` are ready-to-display Bahasa Indonesia. Scores are 0–100.
```
{
  id, session_id, created_at,
  profile: { id, label },                          // the subject profile the lesson was read with
  overall: { score | null, label | null, label_text | null, summary },
                                                   // label: starting | developing | strong; label_text: Mulai tumbuh | Berkembang | Kuat
                                                   // score is null only when the recording was too short to assess
  strengths: [Item],                               // shown first; never empty
  dimensions: [{                                   // always these six, in this order
    key,                                           // content_accuracy | teaching_flow | clarity | engagement | pacing | delivery
    title,                                         // e.g. "Kejelasan"
    score | null, label | null, label_text | null,
    weight,                                        // share of the overall score, in percent
    available,                                     // false when it could not be measured
    locked,                                        // true when the tier does not include it
    unavailable_reason | null,
    parameters: [{ key, title, score | null, max, available, source }],   // source: llm | computed; empty when locked
    items: [Item]                                  // at most one worked and one noticed, worked first
  }],
  ideas: [Idea],                                   // at most 3
  tip | null,                                      // one line, the first idea
  metrics: { words_per_minute, pause_count, questions_asked, wait_time_avg_ms | null, reading_share | null,
             response_time_avg_ms | null, filler_count, time_per_slide: [{ page, ms }] },
  moments: [{ t_ms, kind, text }],                 // kind: voice | face | both; where voice and face came alive
  questions: [Exchange],                           // every exchange with an AI student, in time order
  examples: [WorkedExample]                        // the teacher's handwritten worked examples, in page order; [] when none
}
WorkedExample: { example_id, page, shown_at_ms | null, shown_ms, confirmed, reading | null, check | null, items: [Item] }
            // `reading` and `check` as in `Example`; `check` is null unless confirmed
            // `shown_at_ms` is when it was first on stage (null if never), `shown_ms` how long in total
            // `items`: at most one worked and one noticed about this example, worked first; empty unless confirmed and shown
Exchange: { event_id, kind, persona | null, text, asked_at_ms, level | null, teacher_question | null,
            answer_quote | null, response_time_ms | null, satisfied | null, follow_up | null }
            // kind regular | misconception | capstone: `text` is the student's question, `answer_quote` what the teacher answered,
            //   `satisfied` whether the student showed it landed, `follow_up` the student's one follow-up if any
            // kind answer: `teacher_question` is what the teacher asked the class, `text` the student's answer,
            //   `answer_quote` how the teacher carried on
Item: { id, kind, text, quote | null, t_ms | null, page | null }   // kind: worked | noticed
            // `page` is set when `quote` is a line the teacher wrote in a worked example; `t_ms` is then when that page was first shown
Idea: { id, text, ready_to_use }                      // ready_to_use: the example, story or question, written in Bahasa Indonesia
```
- The same shape exists as a Pydantic class, `app.services.report_schema.ReportOut`, for use as the endpoint's `response_model`.
- `delivery` ("Suara & ekspresi") is voice-only when the camera is off, and unavailable only when no signal bins were sent.
- Only a worked example that is confirmed and was shown on stage counts: it adds the parameters `worked_example` (in `content_accuracy`) and `worked_steps` (in `clarity`). Without one, both come back with `available: false` and the cards score as they always did.
- The parameters and weights behind each card are in `docs/delivery-grading.md`.

`POST /reports/{id}/flags` — `{ item_id }` → 204. "This is not accurate"; the item is hidden from then on.
- `item_id` is the `id` of an item in `strengths`, `ideas` or a dimension's `items`; any other id gives 404. Flagging twice is the same as once.

## Schedule

`GET /schedule` → `[{ id, datetime, subject, chapter, session_id | null }]`, earliest first. Read-only: the user's rows in the `schedule` table; nothing creates them yet.

## Health

`GET /health` → `{ "status": "ok" }`
