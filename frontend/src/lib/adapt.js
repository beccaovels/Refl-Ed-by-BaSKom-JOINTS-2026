import { growthLabel } from './data.js';

// Turns the backend Report (docs/api-contract.md) into the shape the report page draws.
// Scores are 0-100, the same as the backend (docs/api-contract.md).
const TITLES = {
    content_accuracy: 'Ketepatan materi',
    teaching_flow: 'Alur mengajar',
    clarity: 'Kejelasan',
    engagement: 'Keterlibatan murid',
    pacing: 'Tempo',
    delivery: 'Suara & ekspresi',
    on_camera_presence: 'Suara & ekspresi',
};
const toScore = (s) => (s === null || s === undefined ? null : Math.round(s));
const plain = (text) =>
    String(text ?? '')
        .toLowerCase()
        .replace(/[^\p{L}\p{N}]+/gu, ' ')
        .trim();

export function adaptReport(report, { id, lesson, material, camera, seconds, moments }) {
    const evidenceIndex = (item) => {
        if (!item?.quote) return undefined;
        const wanted = plain(item.quote);
        const i = moments.findIndex((m) => m.speaker === 'Guru' && plain(m.text).includes(wanted));
        return i >= 0 ? i : undefined;
    };
    const dimensions = (report.dimensions ?? []).map((d) => {
        const name = d.title ?? TITLES[d.key] ?? d.key;
        if (d.locked) return { name, score: null, summary: 'Tersedia pada paket Institusi.' };
        if (!d.available || d.score === null || d.score === undefined)
            return { name, score: null, summary: d.unavailable_reason ?? 'Belum bisa diukur pada sesi ini.' };
        const worked = (d.items ?? []).find((i) => i.kind === 'worked');
        const noticed = (d.items ?? []).find((i) => i.kind === 'noticed');
        const summary =
            [worked?.text, noticed?.text].filter(Boolean).join(' ') || 'Belum ada catatan untuk bagian ini.';
        const score = toScore(d.score);
        return {
            name,
            score,
            label: d.label_text ?? growthLabel(score),
            summary,
            evidence: evidenceIndex(worked ?? noticed),
        };
    });
    const overall = toScore(report.overall?.score);
    return {
        id,
        lesson,
        material,
        completedAt: report.created_at ?? new Date().toISOString(),
        duration: Math.max(1, Math.ceil(seconds / 60)),
        overall,
        label: overall === null ? null : (report.overall?.label_text ?? growthLabel(overall)),
        scale: 100,
        status: overall === null ? 'limited' : 'complete',
        camera,
        demo: false,
        backendReportId: report.id,
        summary: report.overall?.summary ?? null, // the backend's own words about this lesson
        dimensions,
        moments,
        strengths: (report.strengths ?? []).map((s) => (s.quote ? `${s.text} “${s.quote}”` : s.text)),
        actions: (report.ideas ?? [])
            .slice(0, 3)
            .map((i) => (i.ready_to_use ? `${i.text} Contoh untuk diucapkan: “${i.ready_to_use}”` : i.text)),
    };
}
