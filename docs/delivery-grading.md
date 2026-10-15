# Grading and feedback rules

For developers writing scoring code and prompts, and for UIUX designing the Report. The reasoning is in `docs/plan.md`.

## Dimensions

Six cards, each scored 0–100 with a growth label: below 50 *Mulai tumbuh* (starting), 50–79 *Berkembang* (developing), 80 and up *Kuat* (strong). A card that cannot be measured is "unavailable" and does not lower the overall score.

| Card (key) | Scored by | Needs | Weight in overall |
|---|---|---|---|
| Accuracy (`content_accuracy`) | LLM against the teacher's own material, quoted | transcript (+ PDF) | 20 |
| Teaching flow (`teaching_flow`) | LLM, quoted | transcript | 15 |
| Clarity (`clarity`) | LLM, quoted; two parameters come from the subject profile | transcript | 20 |
| Engagement (`engagement`) | Mix of computed and LLM | transcript (+ PDF) | 25 |
| Pacing (`pacing`) | Rule on computed metrics | transcript timestamps | 10 |
| Tone & expression (`delivery`) | Rule on signal bins | audio signals; camera optional | 10 |

Overall is the weighted mean of the cards the teacher can see (available and not locked).

## Scoring parameters

Every card is 100 points split over named parameters. The code is `backend/app/services/rubric.py`; keep this table and that file the same.

- An **LLM** parameter is judged on a 1–5 scale (1 not seen, 2 once, 3 in part of the lesson, 4 clear and repeated, 5 clear and consistent) and earns level ÷ 5 × weight. A 4 or 5 needs a quote that is really in the transcript; without one it drops to 3.
- A **computed** parameter uses a target band: full marks anywhere inside the comfortable range, sliding down only toward the extremes. Its lowest value earns what level 1 earns, so both kinds share one scale.
- The LLM never sets a card score. It gives levels; code does the arithmetic.
- A parameter that could not be measured (no PDF, no student question answered, camera off) gives its weight to the rest of its card.

| Card | Parameter | Points | How |
|---|---|---|---|
| Accuracy | Statements agree with the teacher's own material | 50 | LLM |
| | Terms, formulas, facts used correctly | 30 | LLM |
| | Student questions answered correctly | 20 | LLM; only when a student question was answered |
| Teaching flow | Goal said aloud early | 20 | LLM |
| | Links to what students already know | 15 | LLM |
| | Order builds up: understand → apply | 30 | LLM |
| | A worked example or apply moment | 20 | LLM |
| | Reflective close or recap | 15 | LLM |
| Clarity | Subject parameter A (maths: explains why the rule works) | 30 | LLM, from the profile |
| | New terms explained when first used | 25 | LLM |
| | Step by step, one idea at a time | 25 | LLM |
| | Subject parameter B (maths: more than one representation) | 20 | LLM, from the profile |
| Engagement | Hook that creates curiosity (first 90 s) | 15 | LLM |
| | Examples, analogies, daily-life links | 25 | LLM |
| | Invites students in: questions asked + thinking time | 25 | Computed |
| | Builds on student questions | 20 | LLM; only when a student question was answered |
| | Own words vs reading the slide | 15 | Computed; only with a PDF |
| Pacing | Speaking rate in the comfortable band | 40 | Computed |
| | Pauses and thinking time | 25 | Computed |
| | Pace varies between parts | 20 | Computed |
| | Time spread across slides | 15 | Computed; only with two or more slides |
| Tone & expression | Vocal liveliness | 25 | Audio bins |
| | Emphasis at key moments | 20 | Audio bins × transcript |
| | Responsiveness to student questions | 25 | Voice + face in the 5 s after |
| | Facial liveliness and warm moments | 15 | Camera bins |
| | Gestures while explaining | 10 | Camera bins |
| | Stable posture, in frame | 5 | Camera bins |

### Where the target bands come from

Only thinking time rests on published research. The rest are starting values, provisional until tuned on our labelled clips, and are never presented as research findings.

| Limit | Value | Basis |
|---|---|---|
| Thinking time after a question | 3 s | Rowe, "Wait Time: Slowing Down May Be a Way of Speeding Up!", *Journal of Teacher Education* 37(1), 1986, pp. 43–50: teachers typically wait about 1 s; at around 3 s student answers get longer and more students take part |
| Speaking rate | 100–160 words per minute | Adapted from English lecture studies (most lectures 110–190 wpm; listeners prefer about 134–147). Indonesian words are longer, about 2.6 syllables on average, so the same speed is fewer words per minute. No Indonesian classroom measurement found |
| Teacher questions | one every 2 minutes or more | Inside the range studies report (about 9–10 per class hour up to 2–3 per minute). No agreed norm |
| Pauses | 1–6 per minute | Ours |
| Pace variation | 15% spread between pieces | Ours |
| Reading share | full marks up to 15%, lowest at 60% | Ours |
| Longest slide | full marks up to half the lesson | Ours |

Links and open questions: `docs/todo.md`.

### How a teacher's question is recognised

A sentence counts as a question to the class when it ends with "?", or starts with a question word or class-directed opener (apa, siapa, kapan, berapa, di mana, kenapa, mengapa, bagaimana, gimana, apakah, bisakah, "ada yang tahu", "menurut kalian", and similar; the list is `QUESTION_OPENERS` in `metrics.py`). Whisper is also given a punctuated example prompt so it is more likely to write the "?". Live, the LLM call that writes a student's answer confirms the sentence really was a question. Detection accuracy is not measured yet.

## Engagement

The headline card. What each of its parameters looks for:

| Parameter | Looks for | Measured |
|---|---|---|
| Hook | An opening that creates curiosity (*pertanyaan pemantik*, a short story or case) | LLM, quoted, first 90 s |
| Examples and application | Concrete examples, analogies, daily life, local context | LLM, quoted |
| Inviting students in | Questions, checking understanding, thinking time | Computed: questions asked per minute; share followed by a pause of 3 s or more |
| Building on student questions | Answers the AI student and extends with an example | LLM on the answer |
| Own words vs reading | Explaining instead of reading out | Computed: share of speech near word-for-word from the slide on screen. Only runs of 8 words or more count. Unavailable without a PDF |

"Purpose" and "Linking back" are scored under Teaching flow, and voice under Tone & expression, so nothing is counted twice.

## Tone & expression

Voice and face together, so the card works voice-only with the camera off. The aim is to tell an engaging delivery from a flat one without asking for non-stop cheerfulness: what counts is that voice and face come alive at the moments that matter. Every signal is measured against the teacher's own 3 s calibration, so a naturally quiet voice or a naturally serious face is not marked down.

- **Moments, not duration.** Credit comes from lively moments at the right times: the greeting, the key idea, a question to students, answering a student.
- **Smiles only ever add.** A smile counts as a warm moment; not smiling is never a deduction while face and voice are alive in other ways. Only a sustained flat voice and still face lowers the score.
- **Described, never labelled.** "Pada 00:05 suara dan wajah Anda paling hidup saat menyapa murid", never an emotion word.

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

Free: Accuracy, Teaching flow, Clarity, Engagement. Institutional adds Pacing and Tone & expression. A locked card returns no score and no parameters. (Engagement in Free is a proposed change to the PRD, pending team confirmation.)
