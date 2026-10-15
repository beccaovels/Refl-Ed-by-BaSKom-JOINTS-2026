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

- An **LLM** parameter is judged on a 1–5 scale (1 not seen, 2 once, 3 in part of the lesson, 4 clear and repeated, 5 clear and consistent) and earns level ÷ 5 × weight. A 4 or 5 needs a quote that is really the teacher's own words (said in the transcript, or written in a worked example they confirmed); without one it drops to 3.
- A **computed** parameter uses a target band: full marks anywhere inside the comfortable range, sliding down only toward the extremes. Its lowest value earns what level 1 earns, so both kinds share one scale.
- The LLM never sets a card score. It gives levels; code does the arithmetic.
- A parameter that could not be measured (no PDF, no student question answered, no worked example, camera off) gives its weight to the rest of its card.

| Card | Parameter | Points | How |
|---|---|---|---|
| Accuracy | Statements agree with the teacher's own material | 40 | LLM |
| | Terms, formulas, facts used correctly | 24 | LLM |
| | Student questions answered correctly | 16 | LLM; only when a student question was answered |
| | Worked example is worked correctly | 20 | LLM, with the check's notes; only with a worked example that was confirmed and shown |
| Teaching flow | Goal said aloud early | 20 | LLM |
| | Links to what students already know | 15 | LLM |
| | Order builds up: understand → apply | 30 | LLM |
| | A worked example or apply moment | 20 | LLM |
| | Reflective close or recap | 15 | LLM |
| Clarity | Subject parameter A (maths: explains why the rule works) | 24 | LLM, from the profile |
| | New terms explained when first used | 20 | LLM |
| | Step by step, one idea at a time | 20 | LLM |
| | Subject parameter B (maths: more than one representation) | 16 | LLM, from the profile |
| | Working is set out and explained | 20 | LLM, against the profile's practice list; only with a worked example that was confirmed and shown |
| Engagement | Hook that creates curiosity (first 90 s) | 15 | LLM |
| | Examples, analogies, daily-life links | 25 | LLM |
| | Invites students in: questions asked + thinking time | 25 | Computed |
| | Builds on student questions | 20 | LLM; only when a student question was answered |
| | Own words vs reading the slide | 15 | Computed; only with a PDF |
| Pacing | Speaking rate in the comfortable band | 40 | Computed |
| | Pauses and thinking time | 25 | Computed |
| | Pace varies between parts | 20 | Computed |
| | Time spread across slides | 15 | Computed; only with two or more slides. Photos of worked examples are left out: a worked example rightly stays on stage a long time |
| Tone & expression | Vocal liveliness | 25 | Audio bins |
| | Emphasis at key moments | 20 | Audio bins × transcript |
| | Responsiveness to student questions | 25 | Voice + face in the 5 s after |
| | Facial liveliness and warm moments | 15 | Camera bins |
| | Gestures while explaining | 10 | Camera bins |
| | Stable posture, in frame | 5 | Camera bins |

The points in Accuracy and Clarity changed on 13 Oct to make room for the two worked-example parameters. The older parameters kept their ratio (40 : 24 : 16 is 50 : 30 : 20, and 24 : 20 : 20 : 16 is 30 : 25 : 25 : 20), so a lesson with no worked example scores exactly as before.

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
| Own words vs reading | Explaining instead of reading out | Computed: share of speech near word-for-word from the slide on screen. Only runs of 8 words or more count. Unavailable when no slide has text. Speech while a photo of the teacher's own working is on stage is left out: walking through your own working is not reading a slide |

"Purpose" and "Linking back" are scored under Teaching flow, and voice under Tone & expression, so nothing is counted twice.

## Handwritten worked examples

A teacher can photograph a question and their own working and show it in the room. Code: `backend/app/services/examples.py`. Endpoints and shapes: `docs/api-contract.md`.

**The order is fixed, so a misread is never held against the teacher:**

1. **Read.** The model sees the photo and copies what is written. It is told not to correct anything and to mark what it is unsure of.
2. **Confirm.** The teacher sees "Apakah ini yang Anda tulis?" and confirms, or edits any value. Until then nothing is checked, and parts marked unsure are kept from the AI students.
3. **Check.** A second call sees only the confirmed text, never the photo. It works the question out itself, then compares step by step: `follows`, `recheck` or `cannot_tell`.

Reading and checking are separate calls on purpose: a model that reads and checks at once tends to "see" the number that ought to be there.

**What may be said, enforced in code:**

- A step the checker skipped, or was unsure of, is `cannot_tell`, never a guess.
- The final answer gets a verdict only when one was written.
- A note names what is written and what our working gives: "Tertulis n(A) = 5, sedangkan hitungan kami mendapat 6 pasangan." A note that passes a verdict ("salah", "keliru") or uses a banned word is replaced by "Langkah 2 layak dicek ulang."
- A different but valid method, or an equivalent form (6/36 and 1/6), is `follows`.
- Handwriting neatness and photo quality are never scored and never mentioned, for the same reason lighting is not.

**What counts in the score:** only an example that is confirmed and was shown on stage.

| Parameter | Rated on | Rule |
|---|---|---|
| Worked example is worked correctly (Accuracy, 20) | The confirmed working, the check's notes, and what the teacher said while it was on stage | Below level 3 only when the check named a step or the final answer. A slip the teacher corrects aloud is not counted. Unavailable when the check could say nothing |
| Working is set out and explained (Clarity, 20) | The practice list below | The list is the yardstick, not the model's taste |

**The practice list is data in the subject profile** (`worked_example_practice`), not the model's opinion. For Matematika X, Bab 7 Peluang:

| Practice | Source |
|---|---|
| Where the numbers come from is visible: the outcomes counted are written or drawn (list, table, sample-space diagram), not only how many | Student book p. 244; teacher's book p. 257 |
| One step per line, each following from the line before, including the form before and after simplifying | Student book p. 244 (2/36 = 1/18); Pólya, "carrying out the plan" |
| The final answer is written as a conclusion that answers the question | Teacher's book p. 257 ("Oleh karena …, maka …"); Pólya, "looking back" |
| The reason for each step is said aloud, not only the result | Panduan Mata Pelajaran Matematika 2025, p. 11 (reasoning); teacher's book p. 257 |

The books give no fixed layout for a worked example: this chapter has no "Diketahui / Ditanya / Jawab". So no layout is required, and the list above is what the books themselves do. Sources: `docs/rubric-sources.md`.

**Feedback on an example** follows the same three parts as everywhere else. Each confirmed example gets at most one *what worked* and one *what we noticed*, shown beside its photo. An idea about the written working counts toward the report's three ideas, and the tool writes the missing line itself. A quote may be a line the teacher wrote, but only from an example they confirmed: confirmation is what makes handwriting the teacher's own words.

**One departure from our own rule, stated plainly:** accuracy is otherwise judged against the teacher's material, not the model's knowledge. Checking a worked example means the model does the maths itself. That is why the check is worded as "worth another look" with our own working beside it, runs only on text the teacher confirmed, and carries the "Ini tidak akurat" button.

## Tone & expression

Voice and face together, so the card works voice-only with the camera off. The aim is to tell an engaging delivery from a flat one without asking for non-stop cheerfulness: what counts is that voice and face come alive at the moments that matter. Every signal is measured against the teacher's own 3 s calibration, so a naturally quiet voice or a naturally serious face is not marked down.

- **Moments, not duration.** Credit comes from lively moments at the right times: the greeting, the key idea, a question to students, answering a student.
- **Smiles only ever add.** A smile counts as a warm moment; not smiling is never a deduction while face and voice are alive in other ways. Only a sustained flat voice and still face lowers the score.
- **Described, never labelled.** "Pada 00:05 suara dan wajah Anda paling hidup saat menyapa murid", never an emotion word.

How each parameter is computed from the 10-second bins (`backend/app/services/delivery.py`). "Key moments" are the greeting, each question the teacher asks the class, and each answer to a student. All limits are provisional until tuned on our labelled flat-versus-lively clips.

| Parameter | Computed as | Full marks when |
|---|---|---|
| Vocal liveliness | Share of bins with speech whose pitch spread is 2 semitones or more | 40% of bins or more |
| Emphasis at key moments | Share of key moments whose bin is lively, or clearly above the teacher's own usual pitch spread or loudness | Half of the key moments or more |
| Responsiveness | Per student question: answered within 5 s, and voice or face lively while answering | Both, for every question |
| Facial liveliness and warm moments | The better of: share of camera bins where the face moved 0.12 or more from neutral; share of key moments where it did | 30% of bins, or half of the key moments |
| Gestures | Share of camera bins with the hands moving | A quarter of bins or more; lowered a little only when the hands move hard through 90% of the lesson |
| Posture, in frame | Average of upright × face found | 70% or more |

The face is read as four movements from MediaPipe blendshapes: smile, brows up, brows down, cheeks. Each counts the same way, as movement from the teacher's calibrated neutral face, so raised brows on a serious face score like a smile. Jaw movement is left out, because talking alone would look expressive. Pitch is found by autocorrelation and its spread is in semitones, so low and high voices are comparable.

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
- Every quote must be the teacher's own words, verbatim: said in the transcript, or written in a worked example they confirmed. Otherwise the item is dropped.
- Each item has a "this is not accurate" button; a flagged item is hidden.
- The absence of group work or hands-on activities is never scored; a solo rehearsal cannot show them.

## Tiers

Free: Accuracy, Teaching flow, Clarity, Engagement. Institutional adds Pacing and Tone & expression. A locked card returns no score and no parameters. (Engagement in Free is a proposed change to the PRD, pending team confirmation.)
