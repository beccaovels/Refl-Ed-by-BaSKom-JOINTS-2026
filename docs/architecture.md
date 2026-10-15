# Architecture

Short version. The reasoning is in `docs/plan.md`; the AI side file by file, with every request flow, is in `docs/ai-pipeline.md`.

```
Browser (React, localhost:5173)              FastAPI (localhost:8000)    SQLite file
 ├─ mic → 16 kHz PCM → WAV chunks at pauses ──POST /audio──► STT ──► transcript segments ─► app.db
 ├─ camera → MediaPipe (main thread, ~5 fps)                ├─ question engine (LLM + material lookup)
 │    → features → 10 s bins (JSON only) ──POST /signals──► ├─ metrics (pure Python)
 ├─ material viewer (pdf.js) → page turns ───POST /slides─► ├─ worked examples (read photo → teacher confirms → check)
 ├─ photo of handwritten working ──POST /materials/{id}/examples─┘
 └─ room UI: transcript, AI students, HUD   ◄── reply to /audio carries the next student event
                                                             └─ scoring (LLM → JSON schema → quote check)
```

| Layer | Choice |
|---|---|
| Frontend | React + Vite + TypeScript + Tailwind |
| Backend | FastAPI, Python 3.11+ |
| Database | One SQLite file via SQLModel, created on startup |
| Speech-to-text | Groq-hosted `whisper-large-v3` |
| LLM | Gemini Flash with JSON output; when one Gemini model is busy, the next is tried |
| Material lookup | PyMuPDF → chunks per page → closest chunks by shared words (rare words count more). Not embeddings |
| Vision | `@mediapipe/tasks-vision` Face and Pose Landmarker, in the browser only |

Rules:
- Plain REST. Audio chunks are numbered (`seq`); the backend ignores repeats, so the browser can retry safely after a network drop.
- All AI calls go through `services/stt.py` (`transcribe`) and `services/llm.py` (`generate_json`). The provider is chosen in `.env`.
- Video frames never leave the browser, and neither does a shared screen. Audio files are deleted after transcription. A photo of handwritten working is uploaded only when the teacher chooses to, like the PDF.
- Numbers (pace, pauses, reading share, signals) are computed in code. The LLM scores only the quoted dimensions and every quote is string-matched against the transcript.
- Subject and grade differences live in data files in `backend/app/profiles/`, not in code.
- Free-tier quotas are not yet verified; check them with real keys before relying on them.
