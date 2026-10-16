import { lessons } from './data.js';

export function lessonUrl(item, scheduleId) {
    const p = new URLSearchParams({
        kelas: item.kelas,
        subject: item.subject,
        chapter: item.chapter,
        subchapter: item.subchapter,
    });
    if (scheduleId) p.set('scheduleId', scheduleId);
    return `/simulator/setup?${p}`;
}

export const current = () => {
    try {
        return JSON.parse(sessionStorage.getItem('gema-current-lesson') || '');
    } catch {
        return {
            lesson: lessons[0],
            scheduleId: null,
            material: null,
        };
    }
};

export function readDraft() {
    try {
        const d = JSON.parse(localStorage.getItem('gema-draft') || 'null');
        return d && d.id && d.config && Array.isArray(d.moments) ? d : null;
    } catch {
        return null;
    }
}
