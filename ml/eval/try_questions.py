"""Plays a sample lesson through the AI students and prints everything they say.

Shows the three things a student does: ask (with a depth level, and one documented
misconception per lesson), answer when the teacher asks the class, and react once the
teacher has answered. Uses the real LLM from backend/.env and a throwaway in-memory database.
Run from the backend folder:
    python ../ml/eval/try_questions.py                      built-in sample lesson
    python ../ml/eval/try_questions.py path/to/lesson.txt   your own: one sentence per line
"""

import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.models import TeachingSession, TranscriptSegment, User  # noqa: E402
from app.services import questions  # noqa: E402

# Matematika kelas X, Bab 7 Peluang. Written by the team as a stand-in for a real recording.
SAMPLE = """Selamat pagi anak-anak, hari ini kita belajar peluang, dan di akhir pelajaran kalian bisa menentukan peluang dari dua kejadian sekaligus.
Waktu SMP kalian sudah belajar peluang sederhana, misalnya peluang muncul angka satu pada sebuah dadu adalah satu per enam.
Sekarang bayangkan kalian bermain ular tangga dengan dua dadu, satu merah dan satu putih.
Semua hasil yang mungkin dari dua dadu itu kita sebut ruang sampel, dan kalau kita daftar semuanya ada tiga puluh enam pasangan.
Ada yang tahu berapa peluang muncul pasangan satu dan satu?
Betul, satu per tiga puluh enam, karena hanya ada satu pasangan itu dari tiga puluh enam kemungkinan.
Sekarang kita lihat jumlah kedua mata dadu, jumlah tujuh bisa didapat dari enam pasangan berbeda.
Jadi peluang jumlah tujuh adalah enam per tiga puluh enam atau satu per enam.
Tabel yang memuat setiap hasil beserta peluangnya kita sebut distribusi peluang.
Berikutnya uang logam, kalau kita lempar sekali peluang gambar dan angka masing-masing setengah.
Setiap lemparan tidak bergantung pada lemparan sebelumnya, itu yang disebut kejadian saling bebas.
Kalau dua kejadian tidak mungkin terjadi bersamaan, kita sebut kejadian saling lepas.
Misalnya jumlah tujuh dan angka kembar pada dua dadu itu saling lepas, jadi peluangnya boleh langsung dijumlahkan.
Menurut kalian, apakah jumlah delapan dan angka kembar juga saling lepas?
Tidak, karena empat dan empat jumlahnya delapan sekaligus kembar, jadi bagian yang sama harus dikurangi satu kali.
Terakhir, kalau dadu dilempar enam puluh kali, frekuensi harapan muncul angka satu adalah satu per enam kali enam puluh yaitu sepuluh kali.
Jadi hari ini kita sudah belajar ruang sampel, distribusi peluang, kejadian saling lepas, saling bebas, dan frekuensi harapan.
"""

WORDS_PER_MINUTE = 130
GAP_MS = 2_500


def timed(lines: list[str]) -> list[tuple[int, int, str]]:
    """Give each sentence a start and end time, as if spoken at a normal pace with a short pause between."""
    pieces, clock_ms = [], 0
    for text in lines:
        length_ms = round(len(text.split()) / WORDS_PER_MINUTE * 60_000)
        pieces.append((clock_ms, clock_ms + length_ms, text))
        clock_ms += length_ms + GAP_MS
    return pieces


def clock(ms: int) -> str:
    return f"{ms // 60_000:02d}:{ms // 1000 % 60:02d}"


def show(event: dict, seconds: float) -> None:
    name = event["persona"]["name"] if event["persona"] else "-"
    detail = {
        "regular": f"bertanya, tingkat {event['level']}",
        "misconception": f"bertanya (miskonsepsi), tingkat {event['level']}",
        "capstone": f"pertanyaan penutup, tingkat {event['level']}",
        "answer": "menjawab pertanyaan guru",
        "reaction": "sudah paham" if event["satisfied"] else "bertanya lanjutan",
        "nudge": "pengingat",
    }[event["kind"]]
    canned = "  (canned)" if event["text"] in [text for text, _ in questions.CANNED_QUESTIONS] else ""
    print(f"\n    >> {name}, {detail} ({seconds:.1f} s): {event['text']}{canned}\n")


if __name__ == "__main__":
    text = Path(sys.argv[1]).read_text(encoding="utf-8") if len(sys.argv) > 1 else SAMPLE
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    print(f"provider={settings.llm_provider} model={settings.llm_model}\n")

    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    seen: Counter = Counter()
    with Session(engine) as db:
        user = User(name="Guru", email="guru@example.com")
        db.add(user)
        db.commit()
        lesson = TeachingSession(
            user_id=user.id, profile_id="matematika-fase-e", class_name="X-1", subject="Matematika", chapter="Bab 7 Peluang"
        )
        db.add(lesson)
        db.commit()

        for seq, (start_ms, end_ms, said) in enumerate(timed(lines)):
            db.add(TranscriptSegment(session_id=lesson.id, seq=seq, start_ms=start_ms, end_ms=end_ms, text=said))
            db.commit()
            print(f"[{clock(start_ms)}] {said}")
            started = time.perf_counter()
            event = questions.next_event(db, lesson.id, now_ms=end_ms)
            if event:
                seen[event["kind"]] += 1
                show(event, time.perf_counter() - started)

        started = time.perf_counter()
        closing = questions.capstone(db, lesson.id)
        seen[closing["kind"]] += 1
        show(closing, time.perf_counter() - started)

    print("events:", dict(seen))
