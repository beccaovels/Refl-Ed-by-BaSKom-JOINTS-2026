# [BaSKom @ JOINTS] AI teaching simulator

JOINTS Hackathon 2026 (UGM), team BaSKom. The product name is not decided yet.

Indonesian teachers rehearse a lesson in a room that looks like a video call. They present their own material, AI students ask questions live, and afterwards they get a report built from evidence in their own words. It runs locally; nothing is deployed.

## Read first

| File | What it is |
|---|---|
| `docs/team-guide.md` | **Start here.** Setup, daily routine, where every page and module lives, using Claude Code |
| `docs/plan.md` | The full plan: context, architecture, grading, schedule, who does what |
| `docs/api-contract.md` | The agreement between frontend and backend. Change it before changing code |
| `docs/delivery-grading.md` | Grading and feedback rules (UIUX: read this and the room layout in the plan) |
| `docs/prd.md` | The PRD |

## Run it

Clone outside OneDrive (syncing `node_modules` and `.venv` causes file locks).

Backend (Python 3.11+):

```
cd backend
python -m venv .venv            # macOS: python3 -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy ..\.env.example .env       # then fill in your keys. macOS: cp ../.env.example .env
uvicorn app.main:app --reload
```

Check: http://localhost:8000/api/health returns `{"status":"ok"}`.

Frontend:

```
cd frontend
npm install
npm run dev
```

If `frontend/package.json` does not exist yet, the frontend has not been scaffolded. One person does that once; the steps are at the end of `docs/team-guide.md`.

## Working together

- `main` always runs. Work on `name/feature`, open a pull request, merge at least daily.
- Stay inside the folders you own (table in `CLAUDE.md`).
- `.env` and the database are never committed.
- Source PDFs in `docs/references/` are git-ignored because of their size; get them from the team drive.

## Evaluation numbers

To be filled from `docs/evaluation.md` before submission.
