# AI pipeline: open work, weak spots and what is not proven yet

Kept by the AI + PM lead. Last updated Mon 12 Oct. Three parts: what is left to build, what a judge could challenge, and where each scoring limit comes from. Nothing here is hidden from the pitch: an unproven number is said to be unproven.

## 1. Status

| Part | State |
|---|---|
| Speech-to-text and LLM wrappers, with fallback when a Gemini model is busy | Done |
| AI student questions: timing, wording, canned fallback | Done |
| Metrics from transcript timestamps | Done |
| Evidence check (quotes), banned-word and emotion-word check | Done |
| Report: six cards, 0–100, per-parameter scores, ideas | Done, works from audio alone |
| Question depth by grade, misconception question from the teacher's book, LLM capstone | Done for Matematika X |
| AI students answer the teacher's question; "satisfied" signal | Done on the backend; the room has to render it |
| Question detection that does not need Whisper's "?" | Done; accuracy not measured |
| Material retrieval | Done with word overlap; embeddings not built |
| Voice and camera signal code (browser) | Written, typechecked, unit-tested. **Not yet run with a real camera or microphone** |
| Tone & expression card, scored from signal bins | Done; thresholds provisional |
| Evaluation numbers in `docs/evaluation.md` | To do, needs clips |
| Profiles other than Matematika X | To do, data files only |

Matematika X demo chapter: **Bab 7, Peluang**.

## 2. Built on 12 Oct, and what is left of each

### AI students answer the teacher's *pertanyaan pemantik* (built)
- When an audio piece ends with a teacher question, one AI student gives a short answer in that grade's voice, sometimes only partly right, so the teacher has something to build on. Event kind `answer`.
- The answer is written while the teacher pauses (2–6 s in our runs). The backend does not wait for 3 s of silence first, because it only hears from the browser when the next audio piece arrives. If the teacher has already moved on, the room may drop the answer.
- The LLM call that writes the answer also confirms the sentence really was a question to the class; "paham ya?" gets no answer. At most one answer per 45 s. If the provider fails, the student stays silent.
- Left: BE+FE 1 renders it in the room; decide in the room whether a late answer is shown or dropped.

### Satisfied signal (built)
- After the teacher has answered for 8 s (or 40 s have passed), the student who asked sends a `reaction` event. `satisfied: true` comes with a short acknowledgement; the frontend shows a gesture on that student's tile and the teacher carries on.
- `satisfied: false` comes with one short, polite follow-up. The next reaction is always satisfied, so a teacher is never stuck. No new question is asked while one is open. If the provider fails, the student is satisfied.
- Left: the gesture design is the frontend's.

### Question detection without relying on Whisper's punctuation (built, not measured)
1. Whisper is sent a `prompt` of punctuated Indonesian classroom speech. Documented to steer style by example, and documented as not fully reliable. **Not yet tried on real Indonesian audio.** If Whisper echoes the prompt back on silence, that text is dropped.
2. A sentence counts as a question with a "?", or when it starts with a question word or class-directed opener (list in `metrics.py`).
3. Live, the answer-writing LLM call confirms it.
- Left: hand-count teacher questions in our clips and report detected vs actual in `docs/evaluation.md`. Stretch: rising pitch at the end of a piece as a third signal.

### Questions by subject and grade (built for Matematika X)
- The profile sets the kinds of questions, what the students already know, example sparking questions from the book, and a depth ladder: level 1 clarify, 2 why/how, 3 what-if. Grade X starts at 1–2 and allows one level 3 per lesson. Each question carries its `level`.
- Five misconceptions for Bab 7 Peluang, copied from the teacher's book with page numbers; one is asked per lesson, the one whose topic the teacher mentioned last.
- Left: the other profiles; a table of level mix per grade in `docs/evaluation.md`, which needs a grade XI profile to compare against.

### Material retrieval (built with word overlap)
- Questions see the slide on screen plus the two other chunks of the PDF closest to what is being said. Accuracy in the report is read against the pages the teacher showed.
- "Closest" is shared words, weighted so rare words count more. It is not embeddings. Say "retrieval" in the pitch, not "embeddings", unless they get built.

### Voice and camera signals (built 13 Oct, not run live)
- `frontend/src/features/simulator/vision/`: pitch and loudness from the microphone, face and body from MediaPipe, 3 s calibration, 10 s bins. One entry point, `startSignals()`. Camera off, camera refused and models failing to load all fall back to voice only.
- `backend/app/services/delivery.py` scores the Tone & expression card from the bins and lists the lesson's liveliest moments.
- `ml/vision-harness/`: typecheck, 23 unit tests, and a page to try it on a webcam, the microphone or a recorded clip.
- Left, in order: (1) open the harness page and confirm the camera path works at all; (2) record and label the paired clips; (3) tune the thresholds; (4) the room calls `startSignals()` and forwards the bins.

### Needed from people
| What | Who | For |
|---|---|---|
| 3 Indonesian audio clips with the exact text spoken, different accents | Team | Word error rate |
| Paired video clips: the same 30–40 s passage delivered flat and engaging, by each of us (bright/dim, glasses, hijab), with each 10 s labelled | Team | Tuning and agreement numbers for voice and face |
| The 2025 *Panduan Mata Pelajaran Matematika* back in `docs/references/` | Lead | `docs/rubric-sources.md` cites its pages; the file is no longer in the folder |
| English teacher's books, grade X and XI | Lead | Two profiles stay hidden until they arrive |
| Demo chapter for Matematika Tingkat Lanjut XI, Biologi XI, Sejarah XI | Lead | Misconception lists |
| At least 2 teachers rating the suggestions | Team | Deck |
| Tell BE+FE 1: `start_ms` and `end_ms` of each audio piece must mark where speech starts and stops | Lead | See 3.2 |

## 3. Weak spots a judge could challenge

### 3.1 Most band limits are our own starting values
Only thinking time rests on published research. Speaking rate is adapted from English lecture studies. The rest have no published norm. See part 4. They become defensible only once tuned on our labelled clips, with agreement numbers.

### 3.2 Pauses depend on how the browser cuts audio
A pause is a gap between two audio pieces. If the room sends back-to-back chunks with no gaps, pause count and thinking time are zero for everyone. The room must cut at silence and send real speech boundaries.

### 3.3 Question detection is not measured
A question is caught by its "?" or by its opening words, so it no longer depends on Whisper's punctuation alone. A question phrased as a statement with rising voice ("Ini saling lepas") is still missed, and a statement that starts with "apa" or "berapa" can be miscounted. No accuracy number yet.

### 3.4 Thinking time counts only a question that ends an audio piece
A question in the middle of a piece, followed straight away by more talk, gets no thinking time. That matches what happened in class (no pause), but depends on 3.2.

### 3.5 Fillers are under-counted
Whisper often drops "eee" and "emm". The count is shown as a number and is not scored.

### 3.6 Reading share needs a text PDF
Scanned slides have no text. Spoken formulas rarely match written ones word for word, so maths slides under-count reading.

### 3.7 Timing is accurate to one audio piece
Response time and thinking time are as precise as the piece boundaries, not to the millisecond.

### 3.8 Scores move between runs
Three runs of the sample lesson gave an overall of 63, 58 and 56. Two causes: the free-tier Gemini model was busy (503) and a different fallback model answered each time; and the first run used different lesson timing. Target is a difference of 10 points or less on the same lesson. Not measured properly yet. Options if it fails: pin one model for scoring, or score twice and average.

### 3.9 Free-tier availability
`gemini-3.8-flash` returned 503 "high demand" or timed out all afternoon on 12 Oct. The code falls back to `gemini-3.5-flash-lite`, then `gemini-2.5-flash`, and skips a model for 2 minutes after it fails; with that, a student's reply took 2–6 s. There is no OpenAI key. If all Gemini models are busy, questions fall back to canned ones, students stay satisfied and silent, and the report fails with a clear error.

### 3.10 The LLM rates 16 parameters in one call
Cheap and fast (about 10 s), but one call carries the whole judgement. The evidence check limits the damage: no quote, no item; a 4 or 5 without a real quote falls to 3. The strong-versus-weak sample test is what shows it discriminates. Not run yet.

### 3.11 No model is trained
Whisper transcribes; it does not hear tone. Tone comes from pitch and loudness measured in the browser. Vision uses pretrained MediaPipe landmarks with our own feature layer. "Tuning" means setting thresholds on half of our labelled clips and reporting on the other half.

### 3.12 Smiles and expression
A smile counts only as a positive "warm moment"; not smiling is never a deduction while voice and face are alive in other ways. The report describes moments ("suara dan wajah Anda paling hidup saat menyapa murid") and never names an emotion. A code check drops feedback containing words such as "gugup" or "percaya diri".

### 3.13 Wording rules have deliberate exceptions
"kurang dari", "kurang lebih" and "lebih kurang" pass the banned-word check because they are ordinary maths phrases.

### 3.14 Short recordings
Under 40 words the LLM is not called and no score is given.

### 3.15 Misconceptions depend on the teacher's book
They are copied with page numbers, never invented. A chapter whose book lists none ships without misconception questions. The trigger words that decide when a misconception is asked are ours.

### 3.16 The live conversation has only been run on a written lesson
`ml/eval/try_questions.py` plays a typed lesson with made-up timing. In that run the "teacher's answer" was simply the next line of the script, so the follow-up it produced does not show how a real answer is judged. It has not been run with a person speaking.

### 3.17 Students sometimes address the teacher as "Pak" or "Bu"
The prompts forbid it, since the tool does not know the teacher's gender. The model does it anyway at times, so code removes "Pak"/"Bu" at the end of a sentence and turns "Bapak" or "Ibu" into "Bapak/Ibu".

### 3.18 A satisfied student is a generous judge
The reaction prompt tells the student to accept any real attempt at an answer, so the signal means "the teacher responded to the question", not "the answer was correct". Correctness is scored in the report under Accuracy.

### 3.19 The camera code has never seen a camera
The maths is unit-tested with made-up numbers (head turn, slouch, hand speed, pitch of a pure tone). The part that talks to MediaPipe and the microphone has only been typechecked and built. Until someone runs the harness page, treat the camera path as unverified. The fallback in `docs/plan.md` stands: run it on the recorded video after the session and call it post-session delivery analysis.

### 3.20 MediaPipe runs on the main thread, not in a web worker
`docs/plan.md` says a web worker. It reads about 5 frames a second and drops to 2 when a frame takes over 150 ms, which keeps the cost low, but it is not a worker. MediaPipe's loader does not work in the module workers Vite makes in development, and there was no browser to test a workaround in. Say "in the browser", not "in a web worker", unless this changes.

### 3.21 The models are downloaded from a CDN on first use
About 10 MB (face and pose models plus the wasm runtime) from Google's and jsDelivr's servers. No picture leaves the browser, but the first lesson with the camera on needs an internet connection for this, on top of the speech-to-text and LLM calls. They could be bundled into the frontend's `public/` folder.

### 3.22 Every Tone & expression threshold is a guess until the clips exist
2 semitones of pitch spread for a lively voice, 0.12 of face movement, the hand-speed limit, the dark-picture limit: all starting values. Rough support for the pitch figure only: monotone speech is usually described as under about 1.5 semitones of spread and expressive speech as 3 or more; we have not sourced this. No agreement numbers yet.

### 3.23 Pitch detection is simple
Autocorrelation on 43 ms of sound, twenty times a second. It handles a clean voice; background noise, music or two people talking will produce wrong pitches. The spread uses the middle 90% of readings to soften this. Not tested on real speech.

### 3.24 Ten-second bins are coarse for five-second moments
"Reacted when a student asked" is read from the whole bin containing the start of the answer, not from the five seconds after the question. If that proves too blunt on real clips, the bin needs a peak value added, which changes the contract.

### 3.25 The harness packages have known vulnerabilities
`npm install` reports 6 (2 critical) in development tools (the Vite 5 and Vitest 2 lines). It is a local developer page, never deployed. The frontend proper should start on current versions.

## 4. Where the scoring limits come from

| Limit | Value | Basis | Strength |
|---|---|---|---|
| Thinking time after a question | 3 s | Rowe, "Wait Time: Slowing Down May Be a Way of Speeding Up!", *Journal of Teacher Education* 37(1), 1986, pp. 43–50. Teachers typically wait about 1 s; at around 3 s student answers get longer and more students take part. | Good. One summary gives her measured threshold as 2.7 s with "3 s" as the rounded teaching target; we have not read the paper itself. |
| Speaking rate | 100–160 words per minute | English lecture studies: most lectures fall between 110 and 190 wpm, and listeners preferred slower versions (about 134–147 wpm). Indonesian words are longer (about 2.6 syllables on average, Fenk-Oczlon and Fenk), so the same speed gives fewer words per minute. | Indirect. No measurement of Indonesian classroom speech found. |
| Teacher questions | one every 2 minutes or more | Studies report from about 9–10 per class hour up to 2–3 per minute, depending on subject and on what counts as a question. | Weak. Inside the observed range; there is no agreed right rate. |
| Pauses | 1–6 per minute | None found | Our starting value |
| Pace variation | 15% spread between pieces | None found | Our starting value |
| Reading share | full marks up to 15%, lowest at 60% | None found | Our starting value |
| Longest slide | full marks up to half the lesson | None found | Our starting value |

What we say in the pitch: thinking time is cited; speaking rate is adapted from lecture research; the others are set from our own labelled clips and reported with agreement numbers. Until the clips exist, they are provisional.

Links:
- Rowe, wait time: https://en.wikipedia.org/wiki/Mary_Budd_Rowe and https://www.structural-learning.com/research-briefings/wait-time-three-seconds
- Lecture speech rates: https://www.xjtlu.edu.cn/assets/files/publications/etic/issue-7/7_5_dixon_2016.pdf and https://www.timeshighereducation.com/node/13518
- Word length in Bahasa Indonesia: https://indoling.com/ismil/15/abstracts/Fenk.pdf
- Whisper prompting guide: https://developers.openai.com/cookbook/examples/whisper_prompting_guide
- Teacher questioning rates: https://openaccess.marmara.edu.tr/bitstreams/fb86a20c-df28-43d5-8846-a98ad41f9143/download and https://ctujsvn.ctu.edu.vn/index.php/ctujsvn/article/view/1902

## 5. How the computed scores work (short version)

Each computed parameter uses a target band: full marks anywhere inside the comfortable range, sliding in a straight line to the lowest value at the extremes. Points = (0.2 + 0.8 × band value) × the parameter's points; the 0.2 floor equals level 1 on the LLM-rated parameters, so both kinds share one scale. A parameter that cannot be measured gives its points to the rest of its card. Full table: `docs/delivery-grading.md`. Code: `backend/app/services/metrics.py`, `scoring.py`, `rubric.py`.

Worked cases:
- 130 words per minute: 40 of 40. 80 or 185: 24. 60 or below, 210 or above: 8.
- Seven-minute lesson, 4 questions all followed by 3 s of silence: 25 of 25. Two of the four followed by 3 s: 21. No questions: 5.
- Reading share 15% or less: 15 of 15. 30%: 11. 60% or more: 3.
