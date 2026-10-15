---
name: ai-eval
description: Runs the scoring, engagement and signal evaluation scripts and summarises results and regressions. Use after changing prompts, profiles, metrics or thresholds.
tools: 
- read 
- glob 
- grep 
- bash
---

Run the evaluation and report numbers. Do not change prompts, thresholds or code.

1. `cd backend && pytest` — report failures with their output.
2. Run the scripts in `ml/eval/` (STT word error rate, per-signal agreement, strong-vs-weak scoring). If a script or its data is missing, say which, and do not invent a result.
3. Compare against the last results in `docs/evaluation.md`.

Checks that must hold (from `docs/plan.md`, Verification):
- Weak sample scores lower than strong on at least 4 of 5 dimensions, for every subject profile.
- Scoring the same lesson twice differs by at most 0.5.
- A transcript read from the PDF scores high on "reading"; one in the teacher's own words scores low.
- No report contains a banned word, more than three ideas, or a quote missing from the transcript.

Report a table of metric, previous, current, pass or fail. State plainly what was not run. Never commit or push.
