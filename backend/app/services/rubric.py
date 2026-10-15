"""The rubric as data: six cards, their parameters and weights.

Mirrors the "Scoring parameters" table in docs/delivery-grading.md. A parameter
is either judged by the LLM on a 1-5 scale with a quote (`source="llm"`) or
computed from the lesson's numbers (`source="computed"`). Cards, weights and
feedback rules are the same for every subject; only the two profile parameters
of Clarity, and what a clearly set-out worked example looks like, come from the
subject profile.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Parameter:
    key: str
    title: str  # shown to the teacher
    max: int  # points out of the card's 100
    source: str  # llm | computed
    look_for: str = ""  # what the LLM is asked to look for


@dataclass(frozen=True)
class Card:
    key: str
    title: str
    weight: int  # share of the overall score
    parameters: tuple[Parameter, ...]


CARDS: tuple[Card, ...] = (
    Card(
        "content_accuracy",
        "Ketepatan materi",
        20,
        (
            Parameter("material_agreement", "Sesuai dengan materi", 40, "llm",
                      "Pernyataan guru sejalan dengan materi yang ia unggah. Tanpa materi, nilai dari konsistensi penjelasan itu sendiri."),
            Parameter("correct_terms", "Istilah, rumus, dan fakta tepat", 24, "llm",
                      "Istilah, rumus, angka, nama, atau urutan disebutkan dengan tepat."),
            Parameter("answers_correct", "Jawaban untuk murid tepat", 16, "llm",
                      "Jawaban guru atas pertanyaan murid benar secara isi."),
            # Only with a photo of the teacher's own working that they confirmed and showed. Without one the
            # three above keep their ratio: 40 : 24 : 16 is 50 : 30 : 20.
            Parameter("worked_example", "Contoh soal dikerjakan dengan tepat", 20, "llm",
                      "Contoh soal yang ditulis guru sampai pada jawaban yang tepat lewat langkah yang saling mengikuti. "
                      "Pakai catatan pemeriksaan pada bagian contoh soal. Selip yang dibetulkan guru saat menjelaskan tidak dihitung."),
        ),
    ),
    Card(
        "teaching_flow",
        "Alur mengajar",
        15,
        (
            Parameter("purpose", "Tujuan belajar disampaikan", 20, "llm",
                      "Di awal, guru mengatakan apa yang akan dipelajari atau bisa dilakukan murid."),
            Parameter("linking_back", "Mengaitkan dengan yang sudah diketahui", 15, "llm",
                      "Guru merujuk pada pengetahuan atau pelajaran sebelumnya (apersepsi)."),
            Parameter("builds_up", "Urutan dari memahami ke menerapkan", 30, "llm",
                      "Penjelasan tersusun: konsep dulu, lalu penerapan; tiap bagian bersambung ke bagian berikutnya."),
            Parameter("apply_moment", "Ada contoh yang dikerjakan", 20, "llm",
                      "Ada setidaknya satu contoh atau soal yang dikerjakan langkah demi langkah."),
            Parameter("reflective_close", "Penutup yang merangkum", 15, "llm",
                      "Di akhir, guru merangkum atau mengajak murid merefleksikan yang dipelajari."),
        ),
    ),
    Card(
        "clarity",
        "Kejelasan",
        20,
        (
            Parameter("profile_a", "", 24, "llm"),  # title and look_for come from the subject profile
            Parameter("terms_explained", "Istilah baru dijelaskan", 20, "llm",
                      "Setiap istilah baru dijelaskan artinya saat pertama kali dipakai."),
            Parameter("step_by_step", "Selangkah demi selangkah", 20, "llm",
                      "Satu gagasan per langkah; tidak ada lompatan yang membuat murid kehilangan alur."),
            Parameter("profile_b", "", 16, "llm"),
            # Only with a confirmed photo that was shown; look_for is the profile's practice list.
            # Without one the four above keep their ratio: 24 : 20 : 20 : 16 is 30 : 25 : 25 : 20.
            Parameter("worked_steps", "Langkah pengerjaan tertata dan dijelaskan", 20, "llm"),
        ),
    ),
    Card(
        "engagement",
        "Keterlibatan murid",
        25,
        (
            Parameter("hook", "Pembuka yang memancing rasa ingin tahu", 15, "llm",
                      "Dalam 90 detik pertama ada pertanyaan pemantik, cerita singkat, atau kasus yang membuat murid penasaran."),
            Parameter("examples", "Contoh dan kaitan dengan keseharian", 25, "llm",
                      "Contoh konkret, analogi, atau kaitan dengan kehidupan sehari-hari dan lingkungan murid."),
            Parameter("invites_students", "Mengajak murid berpikir", 25, "computed"),
            Parameter("builds_on_questions", "Menanggapi pertanyaan murid", 20, "llm",
                      "Guru menanggapi pertanyaan atau jawaban murid secara langsung dan mengembangkannya, misalnya dengan contoh."),
            Parameter("own_words", "Menjelaskan dengan kata-kata sendiri", 15, "computed"),
        ),
    ),
    Card(
        "pacing",
        "Tempo",
        10,
        (
            Parameter("speaking_rate", "Kecepatan bicara", 40, "computed"),
            Parameter("pauses", "Jeda dan waktu berpikir", 25, "computed"),
            Parameter("pace_variation", "Variasi tempo", 20, "computed"),
            Parameter("slide_balance", "Pembagian waktu antar-salindia", 15, "computed"),
        ),
    ),
    Card(
        "delivery",
        "Suara & ekspresi",
        10,
        (
            Parameter("vocal_liveliness", "Suara yang hidup", 25, "computed"),
            Parameter("emphasis", "Penekanan pada bagian penting", 20, "computed"),
            Parameter("responsiveness", "Tanggapan saat murid bertanya", 25, "computed"),
            Parameter("facial_liveliness", "Wajah yang hidup dan momen hangat", 15, "computed"),
            Parameter("gestures", "Gerak tangan saat menjelaskan", 10, "computed"),
            Parameter("posture", "Postur stabil dan tampak di layar", 5, "computed"),
        ),
    ),
)

# Used when a profile does not name its own two Clarity parameters.
DEFAULT_CLARITY = (
    {"title": "Menjelaskan alasannya", "look_for": "Guru menjelaskan mengapa, tidak hanya menyebutkan apa."},
    {"title": "Lebih dari satu cara penyajian", "look_for": "Gagasan yang sama disajikan dengan lebih dari satu cara."},
)

# Used when a profile does not say what a clearly set-out worked example looks like in its subject.
DEFAULT_PRACTICE = (
    {"title": "Asal jawabannya terlihat", "look_for": "Yang dihitung atau dipakai dituliskan, bukan hanya hasilnya."},
    {"title": "Satu langkah per baris", "look_for": "Tiap baris berisi satu langkah dan mengikuti baris sebelumnya."},
    {"title": "Jawaban akhir menjawab soal", "look_for": "Jawaban akhir ditulis sebagai kesimpulan yang menjawab pertanyaan soal."},
    {"title": "Alasan tiap langkah diucapkan", "look_for": "Saat menjelaskan, guru menyebut mengapa langkah itu dilakukan, bukan hanya hasilnya."},
)  # fmt: skip

LABELS = {"starting": "Mulai tumbuh", "developing": "Berkembang", "strong": "Kuat"}


def growth_label(score: float) -> str:
    if score < 50:
        return "starting"
    if score < 80:
        return "developing"
    return "strong"


def band(value: float, zero_low: float, full_low: float, full_high: float, zero_high: float) -> float:
    """1.0 anywhere inside the comfortable range, sliding to 0.0 at the extremes.

    A target band, not a maximum: more is not better once inside the range.
    """
    if full_low <= value <= full_high:
        return 1.0
    if value < full_low:
        return max((value - zero_low) / (full_low - zero_low), 0.0) if full_low > zero_low else 0.0
    return max((zero_high - value) / (zero_high - full_high), 0.0) if zero_high > full_high else 0.0


def clarity_parameters(profile: dict | None) -> tuple[dict, dict]:
    """The two subject-specific Clarity parameters: title and what to look for."""
    named = (profile or {}).get("clarity_parameters") or []
    if len(named) >= 2:
        return named[0], named[1]
    return DEFAULT_CLARITY


def worked_practice(profile: dict | None) -> list[dict]:
    """What a clearly set-out worked example looks like in this subject: title and what to look for."""
    return list((profile or {}).get("worked_example_practice") or DEFAULT_PRACTICE)
