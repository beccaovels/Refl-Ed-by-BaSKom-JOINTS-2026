// Turns the backend Report (docs/api-contract.md) into the shape the report page draws.
// Scores on the page are out of 5; a backend score above 5 is on the 0-100 scale and is divided by 20.
const TITLES = {
    content_accuracy: 'Ketepatan materi',
    teaching_flow: 'Alur mengajar',
    clarity: 'Kejelasan',
    engagement: 'Keterlibatan murid',
    pacing: 'Tempo',
    delivery: 'Suara & ekspresi',
    on_camera_presence: 'Suara & ekspresi',
};
const toFive = (s) => (s === null || s === undefined ? null : Math.round((s > 5 ? s / 20 : s) * 10) / 10);
const plain = (text) => String(text ?? '').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();

export function adaptReport(report, { id, lesson, material, camera, seconds, moments }) {
    const evidenceIndex = (item) => {
        if (!item?.quote)
            return undefined;
        const wanted = plain(item.quote);
        const i = moments.findIndex(m => m.speaker === 'Guru' && plain(m.text).includes(wanted));
        return i >= 0 ? i : undefined;
    };
    const dimensions = (report.dimensions ?? []).map(d => {
        const name = d.title ?? TITLES[d.key] ?? d.key;
        if (d.locked)
            return { name, score: null, summary: 'Tersedia pada paket Institusi.' };
        if (!d.available || d.score === null || d.score === undefined)
            return { name, score: null, summary: d.unavailable_reason ?? 'Belum bisa diukur pada sesi ini.' };
        const worked = (d.items ?? []).find(i => i.kind === 'worked');
        const noticed = (d.items ?? []).find(i => i.kind === 'noticed');
        const summary = [worked?.text, noticed?.text].filter(Boolean).join(' ') || 'Belum ada catatan untuk bagian ini.';
        return { name, score: toFive(d.score), summary, evidence: evidenceIndex(worked ?? noticed) };
    });
    const overall = toFive(report.overall?.score);
    return {
        id,
        lesson,
        material,
        completedAt: report.created_at ?? new Date().toISOString(),
        duration: Math.max(1, Math.ceil(seconds / 60)),
        overall,
        status: overall === null ? 'limited' : 'complete',
        camera,
        demo: false,
        backendReportId: report.id,
        dimensions,
        moments,
        strengths: (report.strengths ?? []).map(s => (s.quote ? `${s.text} “${s.quote}”` : s.text)),
        actions: (report.ideas ?? []).slice(0, 3).map(i => (i.ready_to_use ? `${i.text} Contoh untuk diucapkan: “${i.ready_to_use}”` : i.text)),
    };
}
