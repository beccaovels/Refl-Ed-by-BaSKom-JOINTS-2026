import {
    ArrowRight,
    BookOpen,
    CircleCheck,
    FileText,
    HeartHandshake,
    MessageCircleQuestion,
    Mic,
    Play,
    Presentation,
    ShieldCheck,
    Target,
} from 'lucide-react';
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

const MISSIONS = [
    'Menghadirkan teman latihan mengajar yang bisa dipakai kapan saja, cukup dengan satu laptop.',
    'Memberi masukan yang berpijak pada kata-kata guru sendiri, sebagai cermin, bukan penilaian.',
    'Menghemat waktu guru: setiap ide langsung siap dipakai, tanpa persiapan atau bahan tambahan.',
    'Menjaga data latihan tetap milik guru, tidak dibagikan kepada siapa pun.',
];

const STEPS = [
    { title: 'Login', body: 'Pilih akun Anda. Tanpa kata sandi.' },
    { title: 'Siapkan pelajaran', body: 'Pilih mata pelajaran dan bab, lalu unggah materi bila ada.' },
    { title: 'Berlatih dan refleksi', body: `Mengajar seperti biasa, jawab ${REFL_NAME}, lalu baca refleksi Anda.` },
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
                        <button type="button" className="landing-link" onClick={() => scrollTo('tentang')}>
                            Tentang kami
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

                <section id="tentang" className="landing-section" aria-labelledby="tentang-title">
                    <span className="landing-kicker">Tentang kami</span>
                    <h2 id="tentang-title">Kesempatan berlatih yang sama untuk setiap guru</h2>
                    <p className="landing-lead">
                        Guru di sekolah dengan banyak sumber daya biasanya mendapat pendampingan dan observasi kelas.
                        Banyak guru lain di seluruh Indonesia belum mendapat kesempatan yang sama. Kami, Tim BaSKom,
                        membuat {APP_NAME} agar akses itu lebih merata.
                    </p>
                    <div className="landing-about">
                        <article className="card landing-vision">
                            <span className="landing-icon">
                                <Target size={20} />
                            </span>
                            <h3>Visi</h3>
                            <p>
                                Setiap guru di Indonesia, di kota maupun di daerah, punya kesempatan yang sama untuk
                                berlatih mengajar dan mendapat masukan yang bermakna.
                            </p>
                        </article>
                        <article className="card landing-mission">
                            <span className="landing-icon">
                                <HeartHandshake size={20} />
                            </span>
                            <h3>Misi</h3>
                            <ul>
                                {MISSIONS.map((m) => (
                                    <li key={m}>
                                        <CircleCheck size={18} />
                                        <span>{m}</span>
                                    </li>
                                ))}
                            </ul>
                        </article>
                    </div>
                </section>

                <section id="mulai" className="landing-section" aria-labelledby="mulai-title">
                    <div className="landing-start">
                        <div className="landing-start-copy">
                            <img className="landing-start-logo" src="./assets/logo.svg" alt="" />
                            <span className="landing-kicker">Mulai sekarang</span>
                            <h2 id="mulai-title">Siap mencoba satu latihan kecil?</h2>
                            <p>Tiga langkah, sekitar dua menit sampai Anda mulai mengajar.</p>
                            <button type="button" className="landing-cta" onClick={onStart}>
                                <span>Login dan mulai berlatih</span>
                                <ArrowRight size={18} />
                            </button>
                        </div>
                        <ol className="landing-steps">
                            {STEPS.map((s, i) => (
                                <li key={s.title}>
                                    <span className="landing-step-number">{i + 1}</span>
                                    <span>
                                        <strong>{s.title}</strong>
                                        <small>{s.body}</small>
                                    </span>
                                </li>
                            ))}
                        </ol>
                    </div>
                </section>
            </main>

            <footer className="landing-footer">© 2026 Tim BaSKom · JOINTS 2026, Universitas Gadjah Mada</footer>
        </div>
    );
}
