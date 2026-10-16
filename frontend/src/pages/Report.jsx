import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
    CalendarDays,
    ChevronLeft,
    CircleCheck,
    Clock3,
    FileText,
    CameraOff,
    ChevronDown,
    RefreshCw,
    AlertCircle,
    Lightbulb,
} from 'lucide-react';
import { useApp } from '../context/AppContext.js';
import { Button } from '../components/Button.jsx';
import { PageHeading } from '../components/PageHeading.jsx';
import { lessonUrl } from '../lib/lesson.js';
import { formatDate, formatScore } from '../lib/data.js';

export function ReportPage() {
    const { id } = useParams();
    const { store } = useApp();
    const r = store.reports.find((x) => x.id === id);
    const [active, setActive] = useState(null);
    const [transcriptOpen, setTranscriptOpen] = useState(false);
    const toFocus = useRef(null);
    // "Lihat bukti" opens the transcript, then moves to the moment once it is on the page
    useEffect(() => {
        if (transcriptOpen && toFocus.current !== null) {
            document.getElementById(`moment-${toFocus.current}`)?.focus();
            toFocus.current = null;
        }
    }, [transcriptOpen, active]);
    if (!r)
        return (
            <div className="page">
                <PageHeading
                    title="Laporan tidak ditemukan"
                    description="Sesi ini tidak ada di penyimpanan lokal peramban."
                    action={
                        <Button to="/history" variant="secondary">
                            Kembali ke riwayat
                        </Button>
                    }
                />
            </div>
        );
    // Order follows the feedback rules: what worked first, then at most three ideas, then the detail behind them.
    const scoreLabel = r.label ?? 'Umpan balik terbatas';
    return (
        <div className="page report-page">
            <div className="report-back">
                <Link to="/history">
                    <ChevronLeft size={17} />
                    {' Riwayat latihan'}
                </Link>
            </div>
            <PageHeading
                title={`${r.lesson.subject} · ${r.lesson.chapter}`}
                description={`${r.lesson.subchapter} · ${r.lesson.kelas} · ${formatDate(r.completedAt)} · ${r.duration} menit`}
            />
            <section className="score-panel" aria-label="Skor latihan">
                <div className="score-ring">
                    <strong>{formatScore(r.overall)}</strong>
                    <span>dari 100</span>
                </div>
                <div className="score-copy">
                    <h2>{scoreLabel}</h2>
                    <p>
                        {r.demo
                            ? 'Angka dan bukti di laporan ini adalah data contoh untuk memperagakan alur, bukan analisis AI terhadap sesi Anda.'
                            : 'Laporan ini disusun dari transkrip sesi Anda. Anda bebas tidak setuju dengan bagian mana pun.'}
                    </p>
                    <div className="score-actions">
                        <Button to={lessonUrl(r.lesson)} icon={RefreshCw}>
                            Latih lagi
                        </Button>
                        <Button
                            to={lessonUrl(r.lesson).replace('/simulator/setup', '/schedule')}
                            variant="secondary"
                            icon={CalendarDays}
                        >
                            Jadwalkan latihan
                        </Button>
                    </div>
                </div>
            </section>
            {r.status !== 'complete' && (
                <div className="notice warning">
                    <AlertCircle size={18} />
                    <span>
                        {r.status === 'limited'
                            ? 'Sesi singkat: bukti belum cukup untuk penilaian penuh.'
                            : 'Umpan balik otomatis belum tersedia dalam mode ini. Anda tetap dapat membaca catatan sesi.'}
                    </span>
                </div>
            )}
            {r.material && (
                <div className="notice neutral">
                    <FileText size={18} />
                    {' Nama materi: '}
                    {r.material}
                    {' · isi PDF tidak disimpan atau dianalisis.'}
                </div>
            )}
            <div className="report-feedback">
                <section className="card report-section strengths">
                    <h2>Yang sudah berjalan baik</h2>
                    {r.strengths.length ? (
                        r.strengths.map((s, i) => (
                            <div className="strength" key={i}>
                                <CircleCheck size={20} />
                                <p>{s}</p>
                            </div>
                        ))
                    ) : (
                        <p className="muted">Belum ada bukti yang cukup untuk menyimpulkan kekuatan sesi.</p>
                    )}
                </section>
                <section className="card report-section ideas">
                    <h2>Ide yang bisa dicoba</h2>
                    {r.actions.slice(0, 3).map((a, i) => (
                        <div className="action-item" key={i}>
                            <Lightbulb size={20} />
                            <p>{a}</p>
                        </div>
                    ))}
                    {!r.actions.length && (
                        <p className="muted">Catat satu hal yang ingin Anda latih pada sesi berikutnya.</p>
                    )}
                </section>
            </div>
            <section className="card report-section dimensions">
                <div className="section-heading">
                    <h2>Yang terlihat dari latihan</h2>
                    <p className="rubric-key">Mulai tumbuh: di bawah 50 · Berkembang: 50–79 · Kuat: 80 ke atas</p>
                </div>
                <div className="dimension-list">
                    {r.dimensions.map((d) => (
                        <div className="dimension" key={d.name}>
                            <div className="dimension-title">
                                <strong>{d.name}</strong>
                                <span>{d.score === null ? 'Tidak tersedia' : `${d.score} / 100`}</span>
                            </div>
                            <div
                                className="score-track"
                                role="img"
                                aria-label={
                                    d.score === null
                                        ? `${d.name}: tidak tersedia`
                                        : `${d.name}: ${d.score} dari 100${d.label ? `, ${d.label}` : ''}`
                                }
                            >
                                <span style={{ width: `${d.score ?? 0}%` }} />
                            </div>
                            <p>{d.summary}</p>
                            {d.evidence !== undefined && (
                                <button
                                    className="evidence-link"
                                    onClick={() => {
                                        toFocus.current = d.evidence;
                                        setActive(d.evidence);
                                        setTranscriptOpen(true);
                                    }}
                                >
                                    <Clock3 size={14} />
                                    {' Lihat bukti '}
                                    {r.moments[d.evidence]?.at}
                                </button>
                            )}
                        </div>
                    ))}
                </div>
                {!r.camera && (
                    <div className="notice neutral">
                        <CameraOff size={18} />
                        {' Kehadiran di kamera tidak dinilai karena sesi ini tanpa data kamera.'}
                    </div>
                )}
            </section>
            <section className="card transcript-section" id="transcript">
                <h2>
                    <button
                        type="button"
                        className="transcript-toggle"
                        aria-expanded={transcriptOpen}
                        aria-controls="transcript-body"
                        onClick={() => setTranscriptOpen((open) => !open)}
                    >
                        <span>
                            Transkrip sesi
                            <small>
                                {r.moments.length
                                    ? ` · ${r.moments.length} bagian · ${transcriptOpen ? 'sembunyikan' : 'tampilkan'}`
                                    : ''}
                            </small>
                        </span>
                        <ChevronDown size={20} className={transcriptOpen ? 'open' : ''} />
                    </button>
                </h2>
                <div id="transcript-body" hidden={!transcriptOpen}>
                    {r.moments.length ? (
                        r.moments.map((m, i) => (
                            <div
                                id={`moment-${i}`}
                                tabIndex={-1}
                                className={`moment ${active === i ? 'highlighted' : ''}`}
                                key={i}
                            >
                                <time>{m.at}</time>
                                <div>
                                    <strong>{m.speaker}</strong>
                                    <p>“{m.text}”</p>
                                </div>
                            </div>
                        ))
                    ) : (
                        <p className="muted">Belum ada transkrip karena layanan transkripsi tidak terhubung.</p>
                    )}
                </div>
            </section>
        </div>
    );
}
