import { useEffect, useState } from 'react';
import { profiles } from '../lib/api.js';

// The lessons a teacher can pick: exactly the chapters in the backend's subject profiles (docs/api-contract.md,
// GET /profiles), one entry per sub-chapter. A lesson outside them would be asked by a student written for something
// else, so nothing is added here. Fetched once per visit.
let known = null; // the lessons, once the backend has answered
let asking = null;

const ROMAN = { 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII' };
export const kelasOf = (grade) => `Kelas ${ROMAN[grade] ?? grade}`;

export const toLessons = (list) =>
    list.flatMap((p) =>
        p.chapters.flatMap((c) =>
            c.subchapters.map((subchapter) => ({
                kelas: kelasOf(p.grade),
                subject: p.subject,
                chapter: c.name,
                subchapter,
            })),
        ),
    );

export function useLessons() {
    const [lessons, setLessons] = useState(known);
    useEffect(() => {
        if (known) return;
        let gone = false;
        asking ??= profiles()
            .then((list) => (known = toLessons(list)))
            .catch(() => []) // unreachable: offer nothing; asked again on the next visit
            .finally(() => {
                asking = null;
            });
        asking.then((result) => !gone && setLessons(result));
        return () => {
            gone = true;
        };
    }, []);
    return lessons; // null until the backend has answered, [] when it has no profile to offer
}

export const sameLesson = (a, b) =>
    a.kelas === b.kelas && a.subject === b.subject && a.chapter === b.chapter && a.subchapter === b.subchapter;
