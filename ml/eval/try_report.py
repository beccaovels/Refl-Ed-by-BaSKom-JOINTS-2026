"""Plays a sample lesson and prints the report the teacher would get.

Uses the real LLM from backend/.env and a throwaway in-memory database.
Run from the backend folder:
    python ../ml/eval/try_report.py                      built-in sample lesson
    python ../ml/eval/try_report.py path/to/lesson.txt   your own: one sentence per line
    python ../ml/eval/try_report.py lesson.txt --json    print the whole report as JSON
    python ../ml/eval/try_report.py --example photo.jpg  also show a photo of handwritten working mid-lesson
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlmodel import Session, SQLModel, create_engine, select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.models import Material, Question, SlideEvent, TeachingSession, TranscriptSegment, User  # noqa: E402
from app.services import evidence, examples, scoring  # noqa: E402
from try_questions import SAMPLE  # noqa: E402

WORDS_PER_MINUTE = 130
GAP_MS = 2_500


def play(db: Session, lines: list[str], profile_id: str = "matematika-fase-e", tier: str = "institutional") -> str:
    """Store `lines` as a lesson with one student question in the middle. Returns the session id."""
    user = User(name="Guru", email="guru@example.com", tier=tier)
    db.add(user)
    db.commit()
    lesson = TeachingSession(
        user_id=user.id, profile_id=profile_id, class_name="X-1", subject="Matematika", chapter="Bab 7 Peluang"
    )
    db.add(lesson)
    db.commit()
    starts = []
    clock_ms = 0
    for seq, text in enumerate(lines):
        # A written sample has no timing, so each sentence lasts as long as it would at a normal speaking pace.
        length_ms = round(len(text.split()) / WORDS_PER_MINUTE * 60_000)
        starts.append(clock_ms)
        db.add(TranscriptSegment(session_id=lesson.id, seq=seq, start_ms=clock_ms, end_ms=clock_ms + length_ms, text=text))
        clock_ms += length_ms + GAP_MS
    asked_at = starts[len(lines) // 2] - 1_000
    db.add(
        Question(
            session_id=lesson.id,
            kind="regular",
            persona=json.dumps({"name": "Dimas", "style": "murid"}),
            text="Kenapa peluang jumlah tujuh lebih besar daripada jumlah dua?",
            asked_at_ms=asked_at,
            answered_at_ms=asked_at + 1_000,
        )
    )
    db.commit()
    return lesson.id


def show_example(db: Session, session_id: str, photo: Path) -> None:
    """Add a photo of handwritten working to the lesson: read it, confirm it as read, and show it mid-lesson."""
    lesson = db.get(TeachingSession, session_id)
    material = Material(user_id=lesson.user_id)
    db.add(material)
    db.commit()
    lesson.material_id = material.id
    db.add(lesson)
    db.commit()
    example = examples.read(db, examples.add(db, material.id, photo.name, str(photo)).id, lesson.subject)
    if example.reading:
        example = examples.confirm(db, example.id, subject=lesson.subject)
    starts = [s.start_ms for s in db.exec(select(TranscriptSegment).where(TranscriptSegment.session_id == session_id))]
    db.add(SlideEvent(session_id=session_id, page=example.page, t_ms=sorted(starts)[len(starts) // 3]))
    db.commit()


def checks(report: dict, lines: list[str]) -> list[str]:
    """The rules every report must pass. Returns the ones that failed."""
    written = [line for row in report["examples"] if row["confirmed"] for line in scoring._lines(row["reading"])]
    spoken = " ".join(evidence.words(" ".join(lines + written)))  # the teacher's own words, said or written
    items = report["strengths"] + [item for d in report["dimensions"] for item in d["items"]]
    items += [item for row in report["examples"] for item in row["items"]]
    failed = []
    if not report["strengths"] or report["strengths"][0]["kind"] != "worked":
        failed.append("does not open with a strength")
    if len(report["ideas"]) > 3:
        failed.append("more than three ideas")
    if evidence.banned_words(json.dumps(report, ensure_ascii=False)):
        failed.append(f"banned words: {evidence.banned_words(json.dumps(report, ensure_ascii=False))}")
    for item in items:
        if item["quote"] and " ".join(evidence.words(item["quote"])) not in spoken:
            failed.append(f"quote not in transcript: {item['quote']}")
    return failed


if __name__ == "__main__":
    photo = None
    if "--example" in sys.argv:
        at = sys.argv.index("--example")
        photo = Path(sys.argv[at + 1])
        del sys.argv[at : at + 2]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    text = Path(args[0]).read_text(encoding="utf-8") if args else SAMPLE
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        session_id = play(db, lines)
        if photo:
            show_example(db, session_id, photo)
        started = time.perf_counter()
        report = scoring.build_report(db, session_id)
        took = time.perf_counter() - started

    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(0)

    print(f"provider={settings.llm_provider} model={settings.llm_model}  report in {took:.1f} s\n")
    overall = report["overall"]
    print(f"OVERALL {overall['score']} /100  {overall['label_text']}\n{overall['summary']}\n")
    print("YANG SUDAH BERJALAN BAIK")
    for item in report["strengths"]:
        print(f"  + {item['text']}\n      \"{item['quote']}\"")
    for d in report["dimensions"]:
        state = f"{d['score']} {d['label_text']}" if d["score"] is not None else (d["unavailable_reason"] or "terkunci")
        print(f"\n{d['title'].upper()}  ({d['weight']}%)  {state}")
        for p in d["parameters"]:
            earned = f"{p['score']:>5}/{p['max']}" if p["available"] else "    -/-"
            print(f"    {earned}  {p['title']}  [{p['source']}]")
        for item in d["items"]:
            mark = "+" if item["kind"] == "worked" else "o"
            print(f"  {mark} {item['text']}")
    for row in report["examples"]:
        state = "dikonfirmasi" if row["confirmed"] else "belum dikonfirmasi"
        print(f"\nCONTOH SOAL  halaman {row['page']}  ({state}, tampil {row['shown_ms'] // 1000} s)")
        if row["reading"]:
            print(f"    Soal: {row['reading']['question']}")
            for step in row["reading"]["steps"]:
                print(f"    {step['n']}. {step['text']}")
            print(f"    Jawaban akhir: {row['reading']['final_answer']}")
        if row["check"]:
            print(f"    Pemeriksaan: {row['check']['summary']}")
        for item in row["items"]:
            mark = "+" if item["kind"] == "worked" else "o"
            print(f"  {mark} {item['text']}\n      \"{item['quote']}\"" + ("  (tulisan)" if item["page"] else "  (ucapan)"))
    print("\nIDE YANG BISA DICOBA")
    for idea in report["ideas"]:
        print(f"  * {idea['text']}\n      {idea['ready_to_use']}")
    print(f"\nANGKA  {report['metrics']}")
    failed = checks(report, lines)
    print("\nRULES:", "all passed" if not failed else failed)
