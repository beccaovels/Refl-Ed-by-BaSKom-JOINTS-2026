import { ArrowRight, AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '../../../components/Button.jsx';
import { image } from '../../../lib/data.js';
import { REFL_NAME } from '../../../lib/config.js';

export function CapstoneDialog({ question, pose = 1, answer, onAnswer, onFinish }) {
    return (
        <div className="modal-backdrop">
            <div className="modal capstone-modal" role="dialog" aria-modal="true" aria-labelledby="capstone-title">
                <div className="capstone-head">
                    <img src={`./assets/refl-ask-${pose}.svg`} alt="" draggable="false" />
                    <h2 id="capstone-title">{`${REFL_NAME} punya satu pertanyaan terakhir.`}</h2>
                </div>
                <p>{question}</p>
                <label>
                    {'Catatan jawaban Anda '}
                    <span className="muted">(opsional; jawaban lisan Anda sudah direkam)</span>
                    <textarea
                        rows={4}
                        value={answer}
                        onChange={(e) => onAnswer(e.target.value)}
                        placeholder="Tuliskan inti jawaban untuk disimpan bersama sesi..."
                    />
                </label>
                <Button onClick={onFinish} icon={ArrowRight}>
                    Simpan sesi & lihat refleksi
                </Button>
            </div>
        </div>
    );
}

export function SavingDialog() {
    return (
        <div className="modal-backdrop">
            <div className="modal loading-modal" role="status">
                <img src={image('ui-states/loading-lesson-preparation.png')} alt="" />
                <h2>Menyiapkan refleksi...</h2>
                <p>Menyusun laporan dari transkrip Anda. Biasanya 10-40 detik.</p>
                <div className="loading-bar" />
            </div>
        </div>
    );
}

export function SaveErrorDialog({ onRetry, reason }) {
    return (
        <div className="modal-backdrop">
            <div className="modal" role="alertdialog" aria-modal="true" aria-labelledby="save-error-title">
                <AlertCircle size={26} />
                <h2 id="save-error-title">Sesi belum tersimpan</h2>
                <p>Catatan masih ada. Coba lagi untuk menyimpan satu laporan yang sama.</p>
                {reason && <p className="modal-reason">Penyebab: {reason}</p>}
                <Button onClick={onRetry} icon={RefreshCw}>
                    Coba lagi
                </Button>
            </div>
        </div>
    );
}
