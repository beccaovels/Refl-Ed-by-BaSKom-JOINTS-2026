# Architecture

Short version. The reasoning is in `docs/plan.md`.

```
Browser (React, localhost:5173)              FastAPI (localhost:8000)    SQLite file
 ├─ mic → 16 kHz PCM → WAV chunks at pauses ──POST /audio──► STT ──► transcript segments ─► app.db
 ├─ camera → MediaPipe (web worker, ~5 fps)                 ├─ question engine (LLM + material lookup)
 │    → features → 10 s bins (JSON only) ──POST /signals──► ├─ metrics (pure Python)
 ├─ material viewer (pdf.js) → page turns ───POST /slides─► └─ scoring (LLM → JSON schema → quote check)
 └─ room UI: transcript, AI students, HUD   ◄── reply to /audio carries the next question
```

| Layer | Choice |
|---|---|
| Frontend | React + Vite + TypeScript + Tailwind |
| Backend | FastAPI, Python 3.11+ |
| Database | One SQLite file via SQLModel, created on startup |
| Speech-to-text | Groq-hosted `whisper-large-v3`; OpenAI as fallback |
| LLM | Gemini Flash with JSON output; OpenAI small model as fallback |
| Material lookup | PyMuPDF → chunks per page → embeddings → cosine similarity in NumPy |
| Vision | `@mediapipe/tasks-vision` Face and Pose Landmarker, in the browser only |

Rules:
- Plain REST. Audio chunks are numbered (`seq`); the backend ignores repeats, so the browser can retry safely after a network drop.
- All AI calls go through `services/stt.py` (`transcribe`) and `services/llm.py` (`generate_json`). The provider is chosen in `.env`.
- Video frames never leave the browser. Audio files are deleted after transcription.
- Numbers (pace, pauses, reading share, signals) are computed in code. The LLM scores only the quoted dimensions and every quote is string-matched against the transcript.
- Subject and grade differences live in data files in `backend/app/profiles/`, not in code.
- Free-tier quotas are not yet verified; check them with real keys before relying on them.
