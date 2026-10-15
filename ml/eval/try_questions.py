"""Plays a sample lesson through the question engine and prints what the AI students ask.

Uses the real LLM from backend/.env and a throwaway in-memory database.
Run from the backend folder:
    python ../ml/eval/try_questions.py                      built-in sample lesson
    python ../ml/eval/try_questions.py path/to/lesson.txt   your own: one sentence per line
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.models import TeachingSession, TranscriptSegment, User  # noqa: E402
from app.services import questions  # noqa: E402

SAMPLE = """Selamat pagi anak-anak, hari ini kita belajar fungsi kuadrat.
Coba bayangkan kalian melempar bola basket ke arah ring, lintasan bolanya melengkung naik lalu turun.
Lengkungan seperti itu dalam matematika kita sebut parabola.
Bentuk umum fungsi kuadrat adalah f(x) sama dengan a x kuadrat ditambah b x ditambah c.
Nilai a tidak boleh nol, karena kalau a nol bentuknya menjadi fungsi linear.
Kalau a positif, parabolanya terbuka ke atas, kalau a negatif terbuka ke bawah.
Sekarang kita cari titik puncaknya, yaitu titik tertinggi atau terendah dari grafik.
Rumus sumbu simetrinya adalah x sama dengan negatif b per dua a.
Misalnya f(x) sama dengan x kuadrat dikurangi empat x ditambah tiga.
Maka sumbu simetrinya x sama dengan dua, lalu kita substitusikan sehingga nilai puncaknya negatif satu.
Berikutnya kita lihat diskriminan, yaitu b kuadrat dikurangi empat a c.
Diskriminan menentukan berapa kali grafik memotong sumbu x.
Kalau diskriminannya positif ada dua titik potong, kalau nol ada satu, kalau negatif tidak ada.
Untuk contoh tadi diskriminannya empat, jadi grafiknya memotong sumbu x di dua titik.
Titik potongnya bisa kita cari dengan memfaktorkan, yaitu x sama dengan satu dan x sama dengan tiga.
"""

MS_PER_SENTENCE = 16_000

if __name__ == "__main__":
    lines = (Path(sys.argv[1]).read_text(encoding="utf-8") if len(sys.argv) > 1 else SAMPLE).splitlines()
    print(f"provider={settings.llm_provider} model={settings.llm_model}\n")

    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(name="Guru", email="guru@example.com")
        db.add(user)
        db.commit()
        lesson = TeachingSession(
            user_id=user.id, profile_id="matematika-fase-e", class_name="X-1", subject="Matematika", chapter="Fungsi kuadrat"
        )
        db.add(lesson)
        db.commit()

        for seq, text in enumerate(line.strip() for line in lines if line.strip()):
            start_ms, end_ms = seq * MS_PER_SENTENCE, (seq + 1) * MS_PER_SENTENCE - 1_000
            db.add(TranscriptSegment(session_id=lesson.id, seq=seq, start_ms=start_ms, end_ms=end_ms, text=text))
            db.commit()
            print(f"[{start_ms // 60_000:02d}:{start_ms // 1000 % 60:02d}] {text}")
            started = time.perf_counter()
            event = questions.next_event(db, lesson.id, now_ms=end_ms)
            if event:
                canned = "  (canned: the provider failed)" if event["text"] in questions.CANNED_QUESTIONS else ""
                print(f"\n    >> {event['persona']['name']} ({time.perf_counter() - started:.1f} s): {event['text']}{canned}")
                print(f"       refers to {event['refers_to_ms'] // 1000} s\n")
