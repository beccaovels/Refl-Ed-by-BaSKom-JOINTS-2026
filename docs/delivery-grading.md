# Grading and feedback rules

For developers writing scoring code and prompts, and for UIUX designing the Report. The reasoning is in `docs/plan.md`.

## Dimensions

| Dimension | Scored by | Needs |
|---|---|---|
| Content accuracy | LLM against the teacher's own material, quoted | transcript (+ PDF) |
| Teaching flow | LLM, quoted: is there an apply moment and a reflective close? | transcript |
| Clarity | LLM, quoted, anchors from the subject profile; new terms explained when first used | transcript |
| Engagement | Mix of computed and LLM, see below | transcript (+ PDF) |
| Pacing | Rule on computed metrics | transcript timestamps |
| On-camera presence | Rule on signal bins | camera (optional) |

Scale 1–5 with a growth label: starting, developing, strong. A dimension that cannot be measured is "unavailable" and does not lower the overall score.

## Engagement

| Parameter | Looks for | Measured |
|---|---|---|
| Purpose | The learning goal is said aloud early | LLM, quoted |
| Linking back | A reference to what students already know | LLM, quoted |
| Hook | An opening that creates curiosity (*pertanyaan pemantik*, a short story or case) | LLM, quoted, first 60–90 s |
| Own words vs reading | Explaining instead of reading out | Computed: share of speech near word-for-word from the slide on screen. Only long sustained stretches count. Unavailable without a PDF |
| Examples and application | Concrete examples, analogies, daily life, local context | LLM, each one quoted |
| Inviting students in | Questions, checking understanding, thinking time | Computed: questions asked; pause of 3 s or more after each |
| Building on student questions | Answers the AI student and extends with an example | LLM on the answer + computed response time |
| Voice variation | Emphasis at key points | Computed pitch and volume variation |

## On-camera presence

Weights: responsiveness to student questions 40%, gestures 25%, posture 15%, expression variation 10%, in frame 10%.

| Signal | Good | Lowers it | Never penalised |
|---|---|---|---|
| In frame | In the picture most of the lesson | Long stretches fully out of frame | Lighting, camera quality, background; reading the material; where the eyes point |
| Posture | Stable, upright | Sustained slouch | Moving around |
| Gestures | Some hand movement while explaining | None for minutes, or constant fidgeting | Style or size of gestures |
| Expression | Face changes at meaningful moments | Minutes with no movement at all | Not smiling; a neutral or serious face |
| Voice | Pitch and volume vary; comfortable pace | Long monotone; much too fast or slow | Low energy, accent, dialect |

- Target bands, not maximums: inside the band the score is full; only extremes cost points.
- Responsiveness is measured in the 5 s after each AI question.
- Bins marked `measured: false` (too dark, face not found) are left out, never counted against the teacher.
- No eye contact. No emotion names. Lighting only ever appears as an optional tip before the session.

## How feedback is written

Every item, in this order:
1. **What worked** — first, with a quote and timestamp.
2. **What we noticed** — a plain observation with a timestamp. No adjectives about the teacher.
3. **An idea you could try** — ready to use: the tool writes the story opener, example or question for this chapter, in Bahasa Indonesia, with context the teacher's students would recognise.

Rules, enforced by tests:
- The report opens with strengths.
- At most three ideas per report.
- Ideas need no extra preparation time, materials or devices.
- Banned words: "lacking", "poor", "weak", "should", "kurang", "lemah", "seharusnya". Use "you could try", "one idea" / "Anda bisa mencoba", "satu ide".
- No comparison with other teachers, schools or countries.
- Every quote must appear verbatim in the transcript, otherwise the item is dropped.
- Each item has a "this is not accurate" button; a flagged item is hidden.
- The absence of group work or hands-on activities is never scored; a solo rehearsal cannot show them.

## Tiers

Free: Content accuracy, Teaching flow, Clarity, Engagement. Institutional adds Pacing and On-camera presence. (Engagement in Free is a proposed change to the PRD, pending team confirmation.)
