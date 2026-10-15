# API contract (DRAFT — to be agreed by the team on Fri 9 Oct)

Base URL `http://localhost:8000/api`. JSON unless stated. Ids are UUID strings. Times inside a session are milliseconds from session start (`*_ms`). Errors: `{ "detail": "message" }` with a 4xx/5xx status.

No real auth: after login the frontend sends `X-User-Id: <user id>` on every request.

## Users

`POST /auth/login` — `{ name, email }` → `{ id, name, email, tier }` (`tier`: `free` | `institutional`). Creates the user if new.

## Profiles

`GET /profiles` → `[{ id, subject, grade, phase, label }]`. Only tested profiles are returned.

## Materials

`POST /materials` — multipart, field `file` (PDF, max 20 MB) → `{ id, filename, page_count }`
- 400 if not a PDF; 413 if too large.

`GET /materials/{id}/file` → the PDF (for pdf.js).

## Sessions

`POST /sessions` — `{ profile_id, class_name, subject, chapter, sub_chapter, material_id | null, camera_on, demo_mode }` → `Session`

`Session`: `{ id, status, started_at, ended_at | null, profile_id, class_name, subject, chapter, sub_chapter, material_id, camera_on, demo_mode }` (`status`: `active` | `ended` | `partial`)

`GET /sessions` → `[Session + { overall_score | null }]`, newest first (History, Dashboard).

`GET /sessions/{id}` → `Session`

### Audio

`POST /sessions/{id}/audio` — multipart: `seq` (int, from 0), `start_ms`, `end_ms`, `file` (WAV, 16 kHz mono)

→ `{ seq, segment: { seq, start_ms, end_ms, text } | null, event: Event | null }`

- Idempotent on `(session, seq)`: a repeated `seq` returns the stored result and does nothing else.
- `segment` is null when the chunk had no speech.

`Event`: `{ id, kind, persona: { name, style } | null, text, asked_at_ms, refers_to_ms | null }`
(`kind`: `regular` | `misconception` | `capstone` | `nudge`)

### Slides

`POST /sessions/{id}/slides` — `{ page, t_ms }` → 204. Sent on every page turn, and once for page 1 at start.

### Signals

`POST /sessions/{id}/signals` — `{ bins: [Bin] }` → 204. Idempotent on `(session, t_start_ms)`.

`Bin`: `{ t_start_ms, facing_pct, posture_ok_pct, gesture_rate, expressiveness, face_visible_pct, volume, pitch_variation, measured }`
- Percentages are 0–1. `measured: false` when the picture was too dark or the face was not found; those bins are left out of scoring.
- With the camera off only `t_start_ms`, `volume`, `pitch_variation` are sent; the rest are null.

### Ending

`POST /sessions/{id}/end` → `{ event: Event }` — "Selesai mengajar": returns exactly one capstone question.

`POST /sessions/{id}/finish` → 202 `{ report_status: "pending" }` — after the capstone answer; starts report generation.

## Reports

`GET /sessions/{id}/report` → 200 `Report`, or 202 `{ report_status: "pending" }`, or 500 `{ detail }` if generation failed.

`Report`:
```
{
  id, session_id, created_at,
  overall: { score, label },                       // score 1-5; label: starting | developing | strong
  strengths: [Item],                               // shown first
  dimensions: [{
    key,                                           // content_accuracy | teaching_flow | clarity | engagement | pacing | on_camera_presence
    score | null, label | null,
    available,                                     // false e.g. camera off
    locked,                                        // true when the tier does not include it
    items: [Item]
  }],
  ideas: [Idea],                                   // at most 3
  metrics: { words_per_minute, pause_count, questions_asked, wait_time_avg_ms, reading_share | null, response_time_avg_ms | null, time_per_slide: [{ page, ms }] },
  questions: [{ event_id, kind, text, asked_at_ms, answer_quote | null }]
}
Item: { id, kind, text, quote | null, t_ms | null }   // kind: worked | noticed
Idea: { id, text, ready_to_use }                      // ready_to_use: the example, story or question, written in Bahasa Indonesia
```

`POST /reports/{id}/flags` — `{ item_id }` → 204. "This is not accurate"; the item is hidden from then on.

## Schedule

`GET /schedule` → `[{ id, datetime, subject, chapter, session_id | null }]`

## Health

`GET /health` → `{ "status": "ok" }`
