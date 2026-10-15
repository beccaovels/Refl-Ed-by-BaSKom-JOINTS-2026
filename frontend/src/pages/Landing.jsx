import { BookOpen, FileText, MessageCircleQuestion, Mic, Play, Presentation, ShieldCheck } from 'lucide-react';
import { APP_NAME, REFL_NAME } from '../lib/config.js';

// The public page shown before login. Static: it calls no endpoint and reads no stored data.
// Sections scroll with scrollIntoView, not #anchors, because the HashRouter reads the hash once the teacher logs in.
const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });

const FEATURES = [
    {
        icon: Presentation,
        title: 'Presentasikan materi Anda',
        body: 'Unggah PDF atau foto materi, lalu tampilkan di layar utama seperti berbagi layar di panggilan video.',
    },
    {
        icon: MessageCircleQuestion,
        title: `${REFL_NAME} yang bertanya`,
        body: 'Pertanyaan muncul tentang slide yang sedang tampil, termasuk miskonsepsi yang sering dialami siswa untuk topik itu.',
    },
    {
        icon: FileText,
        title: 'Refleksi dari kata-kata Anda',
        body: 'Setiap catatan mengutip ucapan Anda beserta waktunya. Dimulai dari yang sudah berhasil, dengan paling banyak tiga ide.',
    },
    {
        icon: Mic,
        title: 'Cukup suara',
        body: 'Kamera tidak wajib. Laporan lengkap tetap tersusun dari suara saja, dan ringan untuk laptop sederhana.',
    },
    {
        icon: ShieldCheck,
        title: 'Data tetap milik Anda',
        body: 'Video tidak pernah keluar dari peramban. Laporan hanya bisa dilihat oleh Anda sendiri.',
    },
    {
        icon: BookOpen,
        title: 'Selaras dengan panduan Kemendikdasmen',
        body: 'Rubrik disusun selaras dengan panduan Pembelajaran Mendalam, dengan ide yang langsung siap dipakai di kelas.',
    },
];

export function Landing({ onStart }) {
    return (
        <div className="landing">
            <header className="landing-nav">
                <div className="landing-nav-inner">
                    <img className="landing-logo" src="./assets/logo.svg" alt={APP_NAME} />
                    <nav className="landing-links" aria-label="Navigasi halaman">
                        <button type="button" className="landing-link" onClick={() => scrollTo('fitur')}>
                            Fitur
                        </button>
                        <button type="button" className="landing-cta" onClick={onStart}>
                            Login
                        </button>
                    </nav>
                </div>
            </header>

            <main>
                <section className="landing-hero" aria-labelledby="landing-title">
                    <div className="landing-hero-copy">
                        <span className="landing-kicker">Listen. Ask. Suggest.</span>
                        <h1 id="landing-title">Latih pelajaran Anda, sebelum masuk kelas.</h1>
                        <p>
                            Sajikan materi Anda sendiri seperti di panggilan video. {REFL_NAME} bertanya langsung tentang
                            slide yang sedang tampil, lalu Anda menerima refleksi yang mengutip kata-kata Anda sendiri.
                        </p>
                        <div className="landing-actions">
                            <button type="button" className="button button-primary" onClick={onStart}>
                                <Play size={18} />
                                <span>Mulai berlatih</span>
                            </button>
                            <button type="button" className="button button-secondary" onClick={() => scrollTo('fitur')}>
                                Lihat fitur
                            </button>
                        </div>
                        <small className="landing-note">Tanpa kata sandi · kamera tidak wajib · cukup satu laptop</small>
                    </div>
                    <img
                        className="landing-hero-art"
                        src="./assets/refl-ask-1.svg"
                        alt={`${REFL_NAME}, siswa AI, mengangkat tangan untuk bertanya`}
                    />
                </section>

                <section id="fitur" className="landing-section" aria-labelledby="fitur-title">
                    <span className="landing-kicker">Fitur</span>
                    <h2 id="fitur-title">Seperti kelas sungguhan, tanpa tekanan</h2>
                    <p className="landing-lead">
                        Satu ruang latihan yang terasa seperti panggilan video: materi di tengah, {REFL_NAME} di samping,
                        dan refleksi setelahnya.
                    </p>
                    <div className="landing-features">
                        {FEATURES.map(({ icon: Icon, title, body }) => (
                            <article key={title} className="card landing-feature">
                                <span className="landing-icon">
                                    <Icon size={20} />
                                </span>
                                <h3>{title}</h3>
                                <p>{body}</p>
                            </article>
                        ))}
                    </div>
                </section>
            </main>
        </div>
    );
}
