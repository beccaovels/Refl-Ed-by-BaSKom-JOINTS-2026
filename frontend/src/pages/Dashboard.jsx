import { Link, useNavigate } from 'react-router-dom';
import { ChevronRight, Clock3, FileText, Play, Plus, ArrowRight } from 'lucide-react';
import { useApp } from '../context/AppContext.js';
import { Button } from '../components/Button.jsx';
import { Empty } from '../components/Empty.jsx';
import { PageHeading } from '../components/PageHeading.jsx';
import { useSchedules } from '../hooks/useSchedules.js';
import { lessonUrl, readDraft } from '../lib/lesson.js';
import { describeReport } from '../lib/reportText.js';
import { formatDate, formatScore, formatTime, image, lessons } from '../lib/data.js';
import { APP_NAME } from '../lib/config.js';

export function Dashboard() {
    const { store } = useApp();
    const upcoming = useSchedules()
        .filter((s) => !s.missed && s.status === 'scheduled')
        .slice(0, 3);
    const latest = [...store.reports].sort((a, b) => b.completedAt.localeCompare(a.completedAt))[0];
    return (
        <div className="page">
            <ResumeDraft />
            <PageHeading
                title={store.reports.length ? 'Selamat datang kembali!' : `Selamat datang di ${APP_NAME}!`}
                description="Siap memberi ruang untuk satu latihan kecil hari ini?"
            />
            <section className="hero">
                <div className="hero-content">
                    <h2>Latihan hari ini, lebih percaya diri esok hari.</h2>
                    <p>{`Jelaskan materi, hadapi pertanyaan Siswa ${APP_NAME}, lalu lihat refleksi yang bisa langsung dicoba.`}</p>
                    <Button to="/simulator/setup" icon={Play}>
                        Mulai sesi
                    </Button>
                </div>
                <img
                    src={image('teachers/teacher-explaining-teenagers.png')}
                    alt="Guru menjelaskan materi kepada dua siswa remaja"
                />
            </section>
            <div className="dashboard-grid">
                <section className="card section-card">
                    <div className="section-heading">
                        <div>
                            <h2>Jadwal</h2>
                        </div>
                        <Link to="/schedule" className="text-link">
                            {'Lihat jadwal '}
                            <ArrowRight size={16} />
                        </Link>
                    </div>
                    {upcoming.length ? (
                        <div className="session-stack">
                            {upcoming.map((s) => (
                                <Link to={lessonUrl(s, s.id)} className="schedule-row" key={s.id}>
                                    <span className="date-tile">
                                        <strong>{new Date(s.at).getDate()}</strong>
                                        <small>
                                            {formatDate(s.at, {
                                                month: 'short',
                                            }).toUpperCase()}
                                        </small>
                                    </span>
                                    <span className="row-main">
                                        <strong>
                                            {s.subject}
                                            {' · '}
                                            {s.chapter}
                                        </strong>
                                        <small>
                                            {s.subchapter}
                                            {' • '}
                                            {s.kelas}
                                        </small>
                                        <small>
                                            <Clock3 size={13} />{' '}
                                            {formatDate(s.at, {
                                                weekday: 'long',
                                            })}
                                            {', '}
                                            {formatTime(s.at)}
                                            {' (waktu lokal)'}
                                        </small>
                                    </span>
                                    <ChevronRight size={19} />
                                </Link>
                            ))}
                        </div>
                    ) : (
                        <Empty
                            title="Belum ada latihan terjadwal"
                            body={`Pilih waktu yang cocok, lalu ${APP_NAME} akan mengingatkan saat aplikasi terbuka.`}
                            art="schedule/upcoming-teaching-session.png"
                            action={
                                <Button to="/schedule" variant="secondary" icon={Plus}>
                                    Buat jadwal
                                </Button>
                            }
                        />
                    )}
                </section>
                <section className="card section-card snapshot-card">
                    <div className="section-heading">
                        <div>
                            <h2>Jejak latihan</h2>
                        </div>
                        <Link to="/history" className="text-link">
                            {'Riwayat '}
                            <ArrowRight size={16} />
                        </Link>
                    </div>
                    {latest ? (
                        <>
                            <div className="snapshot">
                                <div className="score-bubble">
                                    {formatScore(latest.overall)}
                                    <small>/ 100</small>
                                </div>
                                <div>
                                    <span className="muted small">{formatDate(latest.completedAt)}</span>
                                    <h3>
                                        {latest.lesson.subject}
                                        {' · '}
                                        {latest.lesson.chapter}
                                    </h3>
                                    <p>{describeReport(latest)}</p>
                                </div>
                            </div>
                            <Button to={`/report/${latest.id}`} variant="secondary" icon={FileText}>
                                Buka laporan
                            </Button>
                        </>
                    ) : (
                        <Empty
                            title="Setiap latihan punya ceritanya"
                            body="Mulai sesi pertama untuk melihat refleksi pribadi Anda di sini."
                            art="brand-elements/reflection-growth.png"
                            action={
                                <Button to="/simulator/setup" variant="secondary">
                                    Mulai latihan
                                </Button>
                            }
                        />
                    )}
                </section>
            </div>
            <TopicCards />
        </div>
    );
}

function ResumeDraft() {
    const navigate = useNavigate();
    const draft = readDraft();
    if (!draft) return null;
    const { lesson } = draft.config;
    const minutes = Math.floor((draft.seconds ?? 0) / 60);
    return (
        <div className="notice-stack">
            <div className="notice-card" role="status">
                <Clock3 size={22} />
                <div className="notice-copy">
                    <strong>Latihan belum selesai</strong>
                    <span title={`${lesson.subject} · ${lesson.chapter}`}>
                        {`${lesson.subject} · ${lesson.chapter} · ${lesson.kelas}`}
                    </span>
                    {minutes > 0 && <small>{`Sudah berjalan ${minutes} menit`}</small>}
                </div>
                <div className="notice-actions">
                    <Button
                        onClick={() => {
                            sessionStorage.setItem('gema-current-lesson', JSON.stringify(draft.config));
                            navigate('/simulator/check');
                        }}
                        variant="secondary"
                    >
                        Lanjutkan
                    </Button>
                </div>
            </div>
        </div>
    );
}

function TopicCards() {
    return (
        <section className="topic-section">
            <div>
                <h2>Satu topik kecil untuk hari ini.</h2>
                <p className="muted small">{`Pilihan materi contoh untuk mencoba ${APP_NAME}.`}</p>
            </div>
            <div className="topic-cards">
                {[lessons[1], lessons[2]].map((l) => (
                    <Link
                        to={lessonUrl(l)}
                        className={`topic-card ${l.subject === 'Biologi' ? 'biology' : ''}`}
                        key={l.subject}
                    >
                        <img
                            src={image(
                                `subjects/${l.subject === 'Biologi' ? 'biology' : 'mathematics'}-card-portrait.png`,
                            )}
                            alt=""
                        />
                        <div>
                            <span>
                                {l.subject}
                                {' · '}
                                {l.kelas}
                            </span>
                            <h3>{l.subchapter}</h3>
                            <small>
                                {'Siapkan latihan '}
                                <ArrowRight size={15} />
                            </small>
                        </div>
                    </Link>
                ))}
            </div>
        </section>
    );
}
