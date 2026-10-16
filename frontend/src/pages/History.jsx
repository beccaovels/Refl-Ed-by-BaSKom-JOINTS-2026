import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CalendarDays, ChevronRight, Play, Sigma, Leaf } from 'lucide-react';
import { useApp } from '../context/AppContext.js';
import { Button } from '../components/Button.jsx';
import { Empty } from '../components/Empty.jsx';
import { PageHeading } from '../components/PageHeading.jsx';
import { formatDate, formatScore } from '../lib/data.js';

export function HistoryPage() {
    const { store } = useApp();
    const [subject, setSubject] = useState('Semua mapel');
    const [chapter, setChapter] = useState('Semua bab');
    const subjects = [...new Set(store.reports.map((r) => r.lesson.subject))];
    const chapters = [
        ...new Set(
            store.reports
                .filter((r) => subject === 'Semua mapel' || r.lesson.subject === subject)
                .map((r) => r.lesson.chapter),
        ),
    ];
    const reports = [...store.reports]
        .filter(
            (r) =>
                (subject === 'Semua mapel' || r.lesson.subject === subject) &&
                (chapter === 'Semua bab' || r.lesson.chapter === chapter),
        )
        .sort((a, b) => b.completedAt.localeCompare(a.completedAt));
    return (
        <div className="page">
            <PageHeading
                title="Riwayat latihan"
                description="Temukan kembali momen belajar Anda. Setiap laporan tersimpan persis seperti saat sesi selesai."
                action={
                    <Button to="/simulator/setup" icon={Play}>
                        Mulai sesi
                    </Button>
                }
            />
            <section className="card history-card">
                <div className="section-heading history-heading">
                    <div>
                        <h2>
                            {'Laporan tersimpan '}
                            <span className="count-pill">{store.reports.length}</span>
                        </h2>
                    </div>
                    <div className="filters">
                        <label className="sr-only" htmlFor="subject-filter">
                            Filter mata pelajaran
                        </label>
                        <select
                            id="subject-filter"
                            value={subject}
                            onChange={(e) => {
                                setSubject(e.target.value);
                                setChapter('Semua bab');
                            }}
                        >
                            <option>Semua mapel</option>
                            {subjects.map((x) => (
                                <option key={x}>{x}</option>
                            ))}
                        </select>
                        <label className="sr-only" htmlFor="chapter-filter">
                            Filter bab
                        </label>
                        <select id="chapter-filter" value={chapter} onChange={(e) => setChapter(e.target.value)}>
                            <option>Semua bab</option>
                            {chapters.map((x) => (
                                <option key={x}>{x}</option>
                            ))}
                        </select>
                    </div>
                </div>
                {reports.length ? (
                    <div className="report-list">
                        {reports.map((r) => (
                            <Link to={`/report/${r.id}`} className="report-row" key={r.id}>
                                <span className="report-subject-icon">
                                    {r.lesson.subject === 'Matematika' ? <Sigma size={22} /> : <Leaf size={22} />}
                                </span>
                                <span className="report-row-copy">
                                    <strong>
                                        {r.lesson.subject}
                                        {' · '}
                                        {r.lesson.chapter}
                                    </strong>
                                    <small>
                                        {r.lesson.subchapter}
                                        {' · '}
                                        {r.lesson.kelas}
                                    </small>
                                    <small>
                                        <CalendarDays size={13} />
                                        {formatDate(r.completedAt)}
                                        {' · '}
                                        {r.duration}
                                        {' menit'}
                                    </small>
                                </span>
                                <span className="report-row-end">
                                    <span
                                        className={`status ${r.status === 'complete' ? 'status-green' : 'status-warn'}`}
                                    >
                                        {r.status === 'complete'
                                            ? 'Selesai'
                                            : r.status === 'limited'
                                              ? 'Terbatas'
                                              : 'Belum tersedia'}
                                    </span>
                                    <strong>{r.overall === null ? '—' : `${formatScore(r.overall)} / 100`}</strong>
                                </span>
                                <ChevronRight size={19} />
                            </Link>
                        ))}
                    </div>
                ) : (
                    <Empty
                        title={store.reports.length ? 'Tidak ada sesi yang cocok' : 'Belum ada riwayat latihan'}
                        body={
                            store.reports.length
                                ? 'Coba pilih mata pelajaran atau bab lain.'
                                : 'Saat sesi pertama selesai, laporan refleksinya akan tampil di sini.'
                        }
                        art="ui-states/loading-lesson-preparation.png"
                        action={
                            store.reports.length ? (
                                <Button
                                    onClick={() => {
                                        setSubject('Semua mapel');
                                        setChapter('Semua bab');
                                    }}
                                    variant="secondary"
                                >
                                    Hapus filter
                                </Button>
                            ) : (
                                <Button to="/simulator/setup" icon={Play}>
                                    Mulai sesi
                                </Button>
                            )
                        }
                    />
                )}
            </section>
        </div>
    );
}
