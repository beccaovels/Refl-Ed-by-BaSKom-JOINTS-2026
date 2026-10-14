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

`POST /materials` — multipart, field `file` (PDF, max 20 MB) → `{ id, filename, page_count }`
- 400 if not a PDF or unreadable; 413 if too large; 500 if it could not be indexed (nothing is kept, the teacher can continue without material).

`GET /materials/{id}/file` → the PDF (for pdf.js; send `X-User-Id` through pdf.js `httpHeaders`). 404 for another user's material.

## Sessions

`POST /sessions` — `{ profile_id, class_name, subject, chapter, sub_chapter, material_id | null, camera_on, demo_mode }` → `Session`
- 422 for an unknown `profile_id` or an empty `class_name`, `subject` or `chapter`; 404 if `material_id` is not the user's.

`Session`: `{ id, status, started_at, ended_at | null, profile_id, class_name, subject, chapter, sub_chapter, material_id, camera_on, demo_mode }` (`status`: `active` | `ended` | `partial`)

`GET /sessions` → `[Session + { overall_score | null, overall_label | null }]`, newest first (History, Dashboard). Both are copied from the stored report; null until it exists.

A session is `active` from creation until `/finish`, then `ended`. `/end` does not close it, so the answer to the closing question is still transcribed.

`GET /sessions/{id}` → `Session`

### Audio

`POST /sessions/{id}/audio` — multipart: `seq` (int, from 0), `start_ms`, `end_ms`, `file` (WAV, 16 kHz mono)

→ `{ seq, segment: { seq, start_ms, end_ms, text } | null, event: Event | null }`

- Idempotent on `(session, seq)`: a repeated `seq` returns the stored result and does nothing else.
- `segment` is null when the chunk had no speech.
- 400 if the file is not WAV; 413 over 10 MB; 422 if `end_ms` < `start_ms`.
- 409 while the same `seq` is still being processed (retry shortly), or for a new `seq` after `/finish`.
- 502 when the speech-to-text or LLM provider failed: nothing was stored, send the same `seq` again.
- The audio is never written to disk.

`Event`: `{ id, kind, persona: { name, style } | null, text, asked_at_ms, refers_to_ms | null }`
(`kind`: `regular` | `misconception` | `capstone` | `nudge`)

### Slides

`POST /sessions/{id}/slides` — `{ page, t_ms }` → 204. Sent on every page turn, and once for page 1 at start.
- A repeat of the same `page` and `t_ms` is ignored. 422 if `page` < 1 or past the material's last page; 409 after `/finish`.

### Signals

`POST /sessions/{id}/signals` — `{ bins: [Bin] }` → 204. Idempotent on `(session, t_start_ms)`.

`Bin`: `{ t_start_ms, facing_pct, posture_ok_pct, gesture_rate, expressiveness, face_visible_pct, volume, pitch_variation, measured }`
- Percentages are 0–1. `measured: false` when the picture was too dark or the face was not found; those bins are left out of scoring.
- With the camera off only `t_start_ms`, `volume`, `pitch_variation` are sent; the rest are null.
- Only these fields are accepted: any other field gives 422, so nothing but these numbers can be uploaded. `t_start_ms` is required; at most 360 bins per request.
- `pitch_variation` is in semitones (≥ 0); every other number is 0–1. Accepted after `/finish` too, for the last bin.

### Ending

`POST /sessions/{id}/end` → `{ event: Event }` — "Selesai mengajar": returns exactly one capstone question. Pressing it again returns the same question; 409 after `/finish`.

`POST /sessions/{id}/finish` → 202 `{ report_status: "pending" }` — after the capstone answer; starts report generation.
- Safe to call again: if the report exists or is being made, nothing new starts; if generation failed, it starts over. One report per session.

## Reports

`GET /sessions/{id}/report` → 200 `Report`, or 202 `{ report_status: "pending" }`, or 500 `{ detail }` if generation failed.
- 404 when `/finish` was never called for this session (or the backend restarted while the report was being made): call `/finish` again.
- The stored report is returned unchanged except that flagged items are left out of `strengths`, `ideas` and each dimension's `items`.

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
- `item_id` is the `id` of an item in `strengths`, `ideas` or a dimension's `items`; any other id gives 404. Flagging twice is the same as once.

## Schedule

`GET /schedule` → `[{ id, datetime, subject, chapter, session_id | null }]`, earliest first. Read-only: the user's rows in the `schedule` table; nothing creates them yet.

## Health

`GET /health` → `{ "status": "ok" }`
