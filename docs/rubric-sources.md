# Rubric sources

Our rubric is **aligned with** these documents. Neither is a teacher-scoring instrument, so never call it "the official rubric". Page numbers are the printed page numbers. PDFs are in `docs/references/` (git-ignored).

## 1. Panduan Mata Pelajaran Matematika, Fase A–F (BSKAP Kemendikdasmen, 2025)

Read: introduction, subject characteristics, section D and its first example plan. Section C (pp. 21–241, per-topic notes) only sampled.

| Page | In the guide | Used for |
|---|---|---|
| 2, 244–245 | Three principles: *berkesadaran, bermakna, menggembirakan* | Sub-headings of Engagement |
| 244 | *Berkesadaran*: students understand the learning goal | Parameter "Purpose" |
| 247 | *Memahami*: connect new knowledge to prior knowledge; stimulate thinking; connect to real and daily-life context | Parameters "Linking back", "Examples and application" |
| 244–245 | *Bermakna*: applying knowledge in personal/local/national/global context | Anchors for "Examples and application" |
| 245 | *Menggembirakan*: a positive, challenging, enjoyable, motivating learning atmosphere | It describes the students' experience, not the teacher's expression |
| 246–250 | Sequence *memahami → mengaplikasi → merefleksi* | Anchors for Teaching flow |
| 11 | Five process elements: reasoning and proof, problem solving, communication, representation, connection | Maths Clarity anchors |
| 3, 268 | Contexts: local wisdom, financial literacy, climate change, health, gender equality | Seed list for suggested examples |
| 273, 276 | Example reflective questions | Few-shot examples for suggestions |
| 265 | Plans adapt to available resources, "with or without technology", and local economic conditions | Backing for the no-extra-materials rule |
| 240 | Integral: "not started from the formula" | Example of a per-topic note in section C |

## 2. Buku Panduan Guru Matematika SD/MI Kelas IV (Pusat Perbukuan, 2022)

Read: contents, general strategy (pp. 18–19), sub-chapter "Pecahan dengan pembilang satu" (pp. 92–96), a sample of the misconception notes. Grade 4 only; 2022 curriculum edition, so used for topic content and misconceptions, not for the framework.

| Page | In the book | Used for |
|---|---|---|
| 92, 97 | *Pengalaman belajar*: the teacher explains what students will be able to do | Confirms "Purpose" |
| 92–93 | *Apersepsi*; *Pertanyaan Esensi/Pemantik* | Confirms "Linking back" and "Hook"; few-shot examples |
| 18 | Contextual learning; *Bertanya*: questions to check understanding and prompt responses | Anchors for "Inviting students in" |
| 34, 44, 48 and 22 more | *Miskonsepsi* block in each sub-chapter | Misconception questions asked by AI students |
| 94–95 | "This activity may be replaced to fit conditions around your students" | Backing for local-context suggestions |

## 3. Buku Panduan Guru Matematika SMA/MA/SMK/MAK Kelas X, Edisi Revisi (Kemendikbudristek, 2023)

Read: contents, Capaian Pembelajaran (pp. 6–7), Bab 7 Peluang (pp. 243–286). Used for the profile `backend/app/profiles/matematika-fase-e.yaml`, demo chapter Bab 7 Peluang.

| Page | In the book | Used for |
|---|---|---|
| 6–7 | Capaian Pembelajaran Fase E, element Analisis Data dan Peluang | `phase_expectation` in the scoring prompt |
| 246 | *Apersepsi* and *pertanyaan pemantik* for the chapter; "Ayo, Mengingat Kembali" (SMP probability) | `example_questions`, `assumed_knowledge` |
| 260, 270 | *Pertanyaan pemantik* for sub-chapters B and C | `example_questions` |
| 249 | Misconception: getting the same number on two dice is harder than different numbers | AI student misconception question |
| 258 | Misconception: an earlier outcome affects the next one although the events are independent | AI student misconception question |
| 261 | "Atau" in probability differs from everyday "or" | AI student misconception question |
| 262 | Experimental probability is assumed to equal theoretical probability | AI student misconception question |
| 265 | Relative frequency and expected frequency are confused | AI student misconception question |
| 257 | A solution shown as a sample-space table, then an *Alternatif Penyelesaian* by reasoning ("peserta didik dapat juga bernalar…"), closing with "Oleh karena …, maka …" | `worked_example_practice`: where the numbers come from is visible; the answer is written as a conclusion; the reason is given. Also the rule that a different valid method is never marked down |

The `ask` line of each misconception in the profile is our wording of the book's misconception in a student's voice; the misconception itself is the book's.

## 4. Buku Siswa Matematika SMA/MA/SMK/MAK Kelas X, Edisi Revisi (Kemendikbudristek, 2023)

Read: Bab 7 Peluang (pp. 240–271), searched for how worked examples are set out.

| Page | In the book | Used for |
|---|---|---|
| 244 | The chapter's one "Contoh": each probability shown on a 6 × 6 sample-space table with the event shaded, and written before and after simplifying (2/36 = 1/18) | `worked_example_practice`: where the numbers come from is visible; one step per line, including the form before and after simplifying |
| 240–271 | No fixed layout for a worked example. "Diketahui / Ditanya / Jawab" does not appear in the chapter | We require no layout; the practice list is what the books do themselves |

## 5. Pólya, *How to Solve It* (Princeton University Press, 1945)

Four phases of solving a problem: understanding the problem, devising a plan, carrying out the plan, looking back. Not an Indonesian curriculum document and not a scoring instrument; used only as a second, general anchor for two items of `worked_example_practice` ("one step per line, each following from the last" for carrying out the plan; "the final answer is written as a conclusion that answers the question" for looking back). Cited from general knowledge of the book; page numbers not checked.

Also in `docs/references/`, not yet read: the teacher's and student books for Matematika Tingkat Lanjut XI (2024), Biologi XI (2022) and Sejarah XI (teacher's book in the older Sekolah Penggerak edition, student book revised 2024).

## Still needed

- *Panduan Mata Pelajaran* for English, history and biology. The 2025 maths guide (source 1) is no longer in `docs/references/` and needs to be put back.
- English teacher's books for grade X and XI.
- A demo chapter for each remaining profile; its misconceptions are then copied from the book (none are invented).
- A published teacher-observation instrument to cite alongside the guides.
- Check, do not assume, that the other subject guides share section D.
