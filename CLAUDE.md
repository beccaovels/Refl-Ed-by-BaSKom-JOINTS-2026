# [BaSKom @ JOINTS] AI teaching simulator

Hackathon project for JOINTS 2026 (UGM), team BaSKom. Submission Thu 15 Oct 2026.
Working name is `[BaSKom @ JOINTS]`. The product name is not decided: do not invent or use one in code, UI text or docs. The UI reads the name from one constant.

## Hard rules (these override any default behaviour)

- claude is NOT ALLOWED TO COLLABORATE, (NOT A COLLABORATOR ON GITHUB)
- claude is not allowed to PUSH TO GITHUB

In practice:
- Never run `git push` or any command that writes to GitHub (`gh pr create`, `gh pr merge`, `gh repo create`, changing remotes). Humans push.
- Never appear as an author or collaborator: no `Co-Authored-By` line, no "Generated with Claude Code" line, no Claude name or email in commits, PR text or files.
- Do not commit unless a person explicitly asks in that message.

## What this is and who it is for

Indonesian teachers rehearse a lesson in a room that looks like a video call. They present their own material, AI students ask questions live, and afterwards they get a report built from evidence in their own words.

- **Who:** teachers across Indonesia, mostly outside big cities, many with little money. One modest laptop; camera and shared material are on the same screen.
- **Why:** teachers in well-resourced schools get coaching and observation; these teachers do not. The aim is equal access to practice, especially moving from reading slides to engaging lessons.
- **Their reality:** low pay and heavy administrative load. The product saves time, never adds work, never treats the teacher as the problem.
- **Stance:** a rehearsal partner and mirror, not a judge. Feedback is input the teacher may ignore.

## Product principles that must never be broken

- No eye-contact scoring. No emotion labels; cheerful is not the goal; a calm serious teacher can score 5.
- Lighting, camera quality and equipment are never scored.
- Camera is optional. A full report works from audio alone.
- Video never leaves the browser. Only small JSON signal bins and audio chunks are uploaded.
- Every qualitative point quotes the teacher's own words with a timestamp; a quote not found in the transcript is dropped.
- Feedback order: what worked, what we noticed, an idea you could try. At most three ideas. No "lacking", "poor", "weak", "should" (nor "kurang", "lemah", "seharusnya"). No comparison with other teachers, schools or countries.
- Suggestions need no extra preparation time, materials or devices; the tool writes the example or story itself.
- Nothing in the product or pitch implies these teachers are low quality. The framing is unequal access to coaching.
- The teacher owns the data. No individual scores to principals.
- The rubric is "aligned with" the Kemendikdasmen guide, never called "the official rubric".
- Local only. No deployment.

## Stack and commands

- Frontend: React + Vite + TypeScript + Tailwind, `localhost:5173`. Run: `cd frontend && npm run dev`
- Backend: FastAPI, Python 3.11+, SQLite via SQLModel, `localhost:8000`. Run: `cd backend && uvicorn app.main:app --reload`
- Tests: `cd backend && pytest`
- AI providers are called only through `backend/app/services/stt.py` and `backend/app/services/llm.py`, switched in `.env`. Free tiers first (Groq Whisper, Gemini Flash); OpenAI is the fallback.
- Vision: `@mediapipe/tasks-vision` in a web worker, in the browser only.

## Who owns what

| Person | Owns |
|---|---|
| AI + PM | `frontend/src/features/simulator/vision/`, `backend/app/services/`, `backend/app/prompts/`, `backend/app/profiles/`, `ml/`, `docs/` |
| BE+FE 1 | Simulator Room: `frontend/src/features/simulator/{audio,stage,room}/`, session lifecycle |
| BE+FE 2 | `backend/app/{api,core,schemas}/`, models, Report / History / Dashboard / Setup pages |
| UIUX | `design/`, landing page, `docs/pitch/` |

Each teammate states their role in a git-ignored `CLAUDE.local.md`. If it is missing and you do not know who you are working with, ask once before editing.
Ask before editing a folder owned by someone other than the person you are working with.
Shared files (`backend/app/main.py`, `requirements.txt`, `frontend/package.json`, `frontend/src/App.tsx`, `frontend/src/lib/`): small additive edits only.
Where each page, endpoint and module lives: `docs/team-guide.md`. Read it before creating a file.
Any change to an endpoint or JSON shape is made in `docs/api-contract.md` in the same change.

## Today's goal

Fri 9 Oct: scaffold, agree `docs/api-contract.md`, database models, everyone runs it locally. Spikes: STT on 3 Indonesian clips, MediaPipe in a worker. Confirm free-tier quotas.

(The lead updates this line each morning.)

## Full context

@docs/plan.md
@docs/api-contract.md

Also read when relevant (not auto-loaded): `docs/delivery-grading.md` (grading and feedback rules), `docs/architecture.md`, `docs/rubric-sources.md`, `docs/prd.md`.
