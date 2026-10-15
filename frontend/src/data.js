export const lessons = [
    { kelas: 'Kelas VII', subject: 'Matematika', chapter: 'Persamaan Linear', subchapter: 'Persamaan satu variabel' },
    { kelas: 'Kelas VII', subject: 'Matematika', chapter: 'Geometri', subchapter: 'Luas segitiga' },
    { kelas: 'Kelas VIII', subject: 'Biologi', chapter: 'Ekosistem', subchapter: 'Rantai makanan' },
    { kelas: 'Kelas VIII', subject: 'Biologi', chapter: 'Sistem Pernapasan', subchapter: 'Proses pertukaran gas' },
];
const dateOffset = (days, hour = 9) => { const d = new Date(); d.setDate(d.getDate() + days); d.setHours(hour, 0, 0, 0); return d.toISOString(); };
const sample = (id, lesson, days, score) => ({ id, lesson, completedAt: dateOffset(days), duration: 8, overall: score, status: 'complete', camera: false, demo: true, moments: [{ at: '00:42', speaker: 'Guru', text: `Hari ini kita akan belajar ${lesson.subchapter.toLowerCase()} melalui contoh di sekitar kita.` }, { at: '03:18', speaker: 'Siswa GeMa', text: `Bagaimana cara menggunakan ${lesson.subchapter.toLowerCase()} dalam kehidupan sehari-hari?` }, { at: '04:06', speaker: 'Guru', text: 'Mari kita pecahkan satu contoh bersama, lalu coba dengan contoh yang berbeda.' }], dimensions: [{ name: 'Ketepatan materi', score: 4, summary: 'Contoh utama sesuai topik latihan.', evidence: 0 }, { name: 'Alur mengajar', score: score >= 4 ? 4 : 3, summary: 'Pembukaan dan latihan tersusun jelas.', evidence: 2 }, { name: 'Kejelasan', score: 4, summary: 'Penjelasan menggunakan contoh konkret.', evidence: 2 }, { name: 'Tempo', score: 3, summary: 'Berikan jeda setelah pertanyaan.', evidence: 1 }, { name: 'Nada & keterlibatan', score: 4, summary: 'Pertanyaan siswa ditanggapi dengan ramah.', evidence: 2 }, { name: 'Kehadiran di kamera', score: null, summary: 'Tidak ada data kamera pada sesi ini.' }], strengths: ['Menghubungkan konsep dengan contoh sehari-hari.', 'Menanggapi pertanyaan siswa dengan langkah yang mudah diikuti.'], actions: ['Setelah menjelaskan satu contoh, berhenti sejenak dan minta siswa menyebutkan langkah berikutnya.', 'Akhiri pelajaran dengan satu soal singkat untuk memeriksa pemahaman.'] });
export function initialStore() { return { mode: 'seeded', reports: [sample('contoh-1', lessons[0], -2, 4.1), sample('contoh-2', lessons[2], -8, 3.8)], schedules: [{ id: 'jadwal-1', ...lessons[1], at: dateOffset(1, 10), status: 'scheduled' }, { id: 'jadwal-2', ...lessons[2], at: dateOffset(3, 15), status: 'scheduled' }] }; }
;
export function readStore() {
    try {
        const v = localStorage.getItem('gema-demo-v1');
        const parsed = v ? JSON.parse(v) : null;
        return isStore(parsed) ? parsed : initialStore();
    }
    catch {
        return initialStore();
    }
}
export function saveStore(value) { localStorage.setItem('gema-demo-v1', JSON.stringify(value)); }
export const formatDate = (v, opts) => new Intl.DateTimeFormat('id-ID', opts ?? { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(v));
export const formatTime = (v) => new Intl.DateTimeFormat('id-ID', { hour: '2-digit', minute: '2-digit' }).format(new Date(v));
export const image = (name) => `./assets/illustrations/${name}`;
/** Demo persistence adapter. Replace at the boundary with authenticated API calls. */
export function switchDemoProfile(store) {
    const next = store.mode === 'seeded' ? 'empty' : 'seeded';
    localStorage.setItem(`gema-profile-${store.mode}`, JSON.stringify(store));
    const saved = localStorage.getItem(`gema-profile-${next}`);
    if (saved) {
        try {
            const value = JSON.parse(saved);
            if (isStore(value))
                return value;
        }
        catch { /* use default */ }
    }
    return next === 'empty' ? { mode: 'empty', reports: [], schedules: [] } : initialStore();
}
export function isStore(value) {
    if (!value || typeof value !== 'object')
        return false;
    const v = value;
    return ['seeded', 'empty'].includes(v.mode) && Array.isArray(v.reports) && Array.isArray(v.schedules) && v.reports.every(r => r && typeof r.id === 'string' && r.lesson && Number.isFinite(Date.parse(r.completedAt)) && Array.isArray(r.dimensions) && Array.isArray(r.moments) && Array.isArray(r.strengths) && Array.isArray(r.actions)) && v.schedules.every(s => s && typeof s.id === 'string' && typeof s.subject === 'string' && Number.isFinite(Date.parse(s.at)));
}
export function lessonFromParams(params) {
    const lesson = lessons.find(l => l.subject === params.get('subject') && l.chapter === params.get('chapter')) ?? lessons[0];
    return { ...lesson, kelas: ['Kelas VII', 'Kelas VIII'].includes(params.get('kelas') ?? '') ? params.get('kelas') : lesson.kelas };
}
export function reportTrends(reports) {
    const groups = new Map();
    for (const r of reports.filter(r => r.overall !== null && r.status === 'complete')) {
        const key = [r.lesson.kelas, r.lesson.subject, r.lesson.chapter, r.demo ? 'demo' : 'real'].join('|');
        groups.set(key, [...(groups.get(key) ?? []), r]);
    }
    return [...groups.values()].filter(g => g.length >= 3).map(g => {
        const last = g.sort((a, b) => a.completedAt.localeCompare(b.completedAt)).slice(-3);
        const values = last.map(r => r.overall);
        return { topic: `${last[2].lesson.subject} · ${last[2].lesson.chapter} · ${last[2].lesson.kelas}`, values, delta: Math.round((values[2] - values[1]) * 10) / 10, demo: last[2].demo };
    });
}
