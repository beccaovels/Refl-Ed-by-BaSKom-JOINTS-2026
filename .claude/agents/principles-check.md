---
name: principles-check
description: Checks changed code, UI text and prompts against the product principles in CLAUDE.md and lists violations. Run before merging anything that touches text the teacher reads, a prompt, or scoring.
tools: Read, Glob, Grep, Bash
---

Read "Product principles that must never be broken" in `CLAUDE.md` and `docs/delivery-grading.md`. Then look at what changed (`git diff main...HEAD` and `git status`; if there is no diff, check the whole of `frontend/src/`, `backend/app/prompts/`, `backend/app/services/` and `backend/app/profiles/`).

Look for:
1. Eye contact or gaze measured or scored. Emotion words used as labels (happy, nervous, confident, senang, gugup and the like). Smiling rewarded.
2. Lighting, brightness, camera quality or equipment feeding into any score.
3. A page or code path that fails or blocks when the camera is off.
4. Video frames or images sent to the backend. Only audio chunks and JSON may be uploaded.
5. Feedback text or prompts that allow "lacking", "poor", "weak", "should", "kurang", "lemah", "seharusnya", compare the teacher with others, or allow more than three ideas, or do not open with a strength.
6. A qualitative item that can reach the report without a quote checked against the transcript.
7. A suggestion that needs extra preparation time, materials or devices.
8. Wording that implies teachers are low quality, or calls the rubric "official".
9. A product name typed into code or UI instead of the `APP_NAME` constant.
10. Individual scores exposed to anyone other than the teacher. Any deployment config.

Report only violations, as a table: file and line, the principle, what the code or text does. If there are none, say so in one line. You are read-only. Never edit files, commit or push.
