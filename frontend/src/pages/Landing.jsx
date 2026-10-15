import { Play } from 'lucide-react';
import { APP_NAME, REFL_NAME } from '../lib/config.js';

// The public page shown before login. Static: it calls no endpoint and reads no stored data.
// Sections scroll with scrollIntoView, not #anchors, because the HashRouter reads the hash once the teacher logs in.
const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });

export function Landing({ onStart }) {
    return (
        <div className="landing">
            <header className="landing-nav">
                <div className="landing-nav-inner">
                    <img className="landing-logo" src="./assets/logo.svg" alt={APP_NAME} />
                    <nav className="landing-links" aria-label="Navigasi halaman">
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
                        </div>
                        <small className="landing-note">Tanpa kata sandi · kamera tidak wajib · cukup satu laptop</small>
                    </div>
                    <img
                        className="landing-hero-art"
                        src="./assets/refl-ask-1.svg"
                        alt={`${REFL_NAME}, siswa AI, mengangkat tangan untuk bertanya`}
                    />
                </section>
            </main>
        </div>
    );
}
