import { useEffect } from 'react';
import { AlertCircle } from 'lucide-react';
import { sameLesson, useLessons } from '../hooks/useLessons.js';

const unique = (xs) => [...new Set(xs)];

// The four pickers, filled only from the backend's subject profiles. Each one narrows the next.
export function LessonFields({ value, onChange }) {
    const lessons = useLessons();
    // A lesson from a link, an old schedule or an earlier visit that the profiles do not offer moves to the closest
    // one that they do: same subject and chapter if possible, else the first lesson.
    useEffect(() => {
        if (!lessons?.length || lessons.some((l) => sameLesson(l, value))) return;
        const close =
            lessons.find((l) => l.subject === value.subject && l.chapter === value.chapter) ??
            lessons.find((l) => l.subject === value.subject) ??
            lessons[0];
        onChange(close);
    }, [lessons, value.kelas, value.subject, value.chapter, value.subchapter]);
    if (lessons && !lessons.length)
        return (
            <div className="notice warning">
                <AlertCircle size={18} />
                <span>
                    Belum ada materi yang bisa dipilih. Server belum punya profil mata pelajaran yang siap; untuk
                    pengembangan lokal, isi SHOW_UNTESTED_PROFILES=true di backend/.env.
                </span>
            </div>
        );
    const all = lessons ?? [];
    const inKelas = all.filter((l) => l.kelas === value.kelas);
    const inSubject = inKelas.filter((l) => l.subject === value.subject);
    const inChapter = inSubject.filter((l) => l.chapter === value.chapter);
    const pick = (list) => list[0] && onChange(list[0]);
    return (
        <div className="field-grid">
            <Picker
                label="Kelas"
                value={value.kelas}
                options={unique(all.map((l) => l.kelas))}
                onChange={(kelas) => pick(all.filter((l) => l.kelas === kelas))}
            />
            <Picker
                label="Mata pelajaran"
                value={value.subject}
                options={unique(inKelas.map((l) => l.subject))}
                onChange={(subject) => pick(inKelas.filter((l) => l.subject === subject))}
            />
            <Picker
                label="Bab"
                value={value.chapter}
                options={unique(inSubject.map((l) => l.chapter))}
                onChange={(chapter) => pick(inSubject.filter((l) => l.chapter === chapter))}
            />
            <Picker
                label="Sub-bab"
                value={value.subchapter}
                options={inChapter.map((l) => l.subchapter)}
                onChange={(subchapter) => onChange({ ...value, subchapter })}
            />
        </div>
    );
}

function Picker({ label, value, options, onChange }) {
    return (
        <label>
            {label}
            <select value={value} disabled={!options.length} onChange={(e) => onChange(e.target.value)}>
                {options.length ? (
                    options.map((x) => <option key={x}>{x}</option>)
                ) : (
                    <option value={value}>Memuat…</option>
                )}
            </select>
        </label>
    );
}
