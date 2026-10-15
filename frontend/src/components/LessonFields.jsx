import { useEffect } from 'react';
import { lessons as allLessons } from '../lib/data.js';
import { useSupportedSubjects } from '../hooks/useSupportedSubjects.js';

export function LessonFields({ value, onChange }) {
    // Only subjects the backend has a profile for; with none known (still loading, or none at all) nothing is hidden.
    const supported = useSupportedSubjects();
    const offered = supported?.size ? allLessons.filter((l) => supported.has(l.subject)) : allLessons;
    const lessons = offered.length ? offered : allLessons;
    const subjects = [...new Set(lessons.map((l) => l.subject))];
    const chapters = lessons.filter((l) => l.subject === value.subject);
    // A lesson that arrived from a link or an earlier visit in a subject that is not offered moves to the first one that is.
    useEffect(() => {
        if (supported?.size && !subjects.includes(value.subject)) onChange({ ...lessons[0], kelas: value.kelas });
    }, [supported, value.subject]);
    return (
        <div className="field-grid">
            <label>
                Kelas
                <select
                    value={value.kelas}
                    onChange={(e) =>
                        onChange({
                            ...value,
                            kelas: e.target.value,
                        })
                    }
                >
                    {['Kelas VII', 'Kelas VIII'].map((x) => (
                        <option key={x}>{x}</option>
                    ))}
                </select>
            </label>
            <label>
                Mata pelajaran
                <select
                    value={value.subject}
                    onChange={(e) => {
                        const next = lessons.find((l) => l.subject === e.target.value);
                        onChange({
                            ...next,
                            kelas: value.kelas,
                        });
                    }}
                >
                    {subjects.map((x) => (
                        <option key={x}>{x}</option>
                    ))}
                </select>
            </label>
            <label>
                Bab
                <select
                    value={value.chapter}
                    onChange={(e) => {
                        const next = chapters.find((l) => l.chapter === e.target.value);
                        onChange({
                            ...next,
                            kelas: value.kelas,
                        });
                    }}
                >
                    {chapters.map((x) => (
                        <option key={x.chapter}>{x.chapter}</option>
                    ))}
                </select>
            </label>
            <label>
                Sub-bab
                <select
                    value={value.subchapter}
                    onChange={(e) =>
                        onChange({
                            ...value,
                            subchapter: e.target.value,
                        })
                    }
                >
                    {chapters
                        .filter((l) => l.chapter === value.chapter)
                        .map((x) => (
                            <option key={x.subchapter}>{x.subchapter}</option>
                        ))}
                </select>
            </label>
        </div>
    );
}
