import { ChartNoAxesCombined, FileText, Play } from 'lucide-react';
import { useApp } from '../context/AppContext.js';
import { Button } from '../components/Button.jsx';
import { Empty } from '../components/Empty.jsx';
import { PageHeading } from '../components/PageHeading.jsx';
import { formatDate, formatScore, reportTrends } from '../lib/data.js';
import { describeReport } from '../lib/reportText.js';

export function PerformanceOverview() {
    const { store } = useApp();
    const reports = [...store.reports].sort((a, b) => b.completedAt.localeCompare(a.completedAt));
    const valid = reports;
    const trends = reportTrends(reports);
    return (
        <div className="page">
            <PageHeading
                title="Performa"
                description="Refleksi pribadi yang membantu Anda memilih latihan berikutnya, tanpa peringkat atau perbandingan dengan guru lain."
                action={
                    <Button to="/simulator/setup" icon={Play}>
                        Mulai sesi
                    </Button>
                }
            />
            {valid.length ? (
                <div className="performance-grid">
                    <section className="card section-card">
                        <p className="card-label">Laporan terakhir</p>
                        <h2>
                            {valid[0].lesson.subject}
                            {' · '}
                            {valid[0].lesson.chapter}
                        </h2>
                        <div className="performance-score">
                            <strong>{formatScore(valid[0].overall)}</strong>
                            <span>/ 100</span>
                        </div>
                        {valid[0].label && <p className="score-label">{valid[0].label}</p>}
                        {describeReport(valid[0]) && <p className="report-description">{describeReport(valid[0])}</p>}
                        <p className="muted">
                            {formatDate(valid[0].completedAt)}
                            {' · '}
                            {valid[0].duration}
                            {' menit'}
                        </p>
                        <Button to={`/report/${valid[0].id}`} variant="secondary" icon={FileText}>
                            Lihat laporan lengkap
                        </Button>
                    </section>
                    <section className="card section-card">
                        <h2>Perkembangan topik</h2>
                        {trends.length ? (
                            <div className="trend-list">
                                {trends.map((t) => (
                                    <div key={t.topic}>
                                        <strong>{t.topic}</strong>
                                        <p>
                                            {t.demo ? 'Data contoh · ' : ''}
                                            {t.delta > 0 ? 'Naik' : t.delta < 0 ? 'Turun' : 'Tetap'} {Math.abs(t.delta)}
                                            {' poin dari sesi sebelumnya'}
                                        </p>
                                        <small>
                                            {t.values.join(' → ')}
                                            {' / 100 · tiga sesi terakhir'}
                                        </small>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <>
                                <p className="muted">
                                    Tren muncul setelah ada sedikitnya tiga sesi pada bab yang sama. Saat ini belum
                                    cukup data untuk menyimpulkan perubahan.
                                </p>
                                <div className="trend-placeholder">
                                    <ChartNoAxesCombined size={30} />
                                    <span>Terus berlatih pada topik yang sama untuk melihat pola.</span>
                                </div>
                            </>
                        )}
                    </section>
                </div>
            ) : (
                <Empty
                    title="Belum ada refleksi"
                    body="Selesaikan satu latihan untuk mulai membangun arsip laporan Anda."
                    art="brand-elements/reflection-growth.png"
                    action={<Button to="/simulator/setup">Mulai sesi</Button>}
                />
            )}
        </div>
    );
}
