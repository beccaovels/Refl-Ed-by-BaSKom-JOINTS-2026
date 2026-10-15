"""Reads photos of handwritten worked examples and prints what the teacher would see.

Uses the real LLM from backend/.env and a throwaway in-memory database.
Run from the backend folder:
    python ../ml/eval/try_example.py photo.jpg [more photos]      what was read; nothing is checked yet
    python ../ml/eval/try_example.py photo.jpg --confirm          then confirm it as read and show the check
    python ../ml/eval/try_example.py photo.jpg --model gemini-2.5-flash   try another model as the reader
    python ../ml/eval/try_example.py photo.jpg --subject Matematika
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.models import Material, User  # noqa: E402
from app.services import examples, rag  # noqa: E402

MARK = {"follows": "sejalan", "recheck": "LAYAK DICEK ULANG", "cannot_tell": "tidak diperiksa"}
UNSURE = "  [belum terbaca jelas]"


def show(db: Session, material: Material, path: Path, subject: str, confirm: bool) -> None:
    example = examples.add(db, material.id, path.name, str(path))
    started = time.perf_counter()
    shown = examples.public(examples.read(db, example.id, subject))
    print(f"\n{path.name}  →  {shown['status']}  ({time.perf_counter() - started:.1f} s)  {shown['status_text']}")
    reading = shown["reading"]
    if not reading:
        return
    print(f"  Soal: {reading['question'] or '(tidak tertulis)'}")
    for step in reading["steps"]:
        print(f"  {step['n']}. {step['text']}{UNSURE if step['unclear'] else ''}")
    print(f"  Jawaban akhir: {reading['final_answer'] or '(tidak tertulis)'}{UNSURE if reading['answer_unclear'] else ''}")
    print(f"  Teks halaman {shown['page']} untuk murid AI: {len(rag.page_text(db, material.id, shown['page']))} karakter")
    if not confirm:
        return

    started = time.perf_counter()
    check = examples.public(examples.confirm(db, example.id, subject=subject))["check"]
    print(f"  Dikonfirmasi apa adanya, lalu diperiksa  ({time.perf_counter() - started:.1f} s)")
    for step in check["steps"]:
        print(f"  {step['n']}. {MARK[step['status']]}" + (f"  —  {step['note']}" if step["note"] else ""))
    print(f"  Jawaban akhir: {MARK[check['answer']]}.  Hitungan kami: {check['our_answer'] or '-'}")
    print(f"  {check['summary']}")


def option(arguments: list[str], name: str) -> str:
    """Take `name value` out of the arguments and return the value, or "" when it is not there."""
    if name not in arguments:
        return ""
    at = arguments.index(name)
    value = arguments[at + 1]
    del arguments[at : at + 2]
    return value


if __name__ == "__main__":
    arguments = sys.argv[1:]
    subject = option(arguments, "--subject")
    settings.llm_vision_model = option(arguments, "--model") or settings.llm_vision_model
    confirm = "--confirm" in arguments
    photos = [argument for argument in arguments if argument != "--confirm"]
    if not photos:
        sys.exit(__doc__)
    print(f"LLM  provider={settings.llm_provider} model={settings.llm_model or '(not set)'} reader={settings.llm_vision_model or '(same)'}")
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(name="Guru", email="guru@example.com")
        db.add(user)
        db.commit()
        material = Material(user_id=user.id)
        db.add(material)
        db.commit()
        for name in photos:
            show(db, material, Path(name), subject, confirm)
