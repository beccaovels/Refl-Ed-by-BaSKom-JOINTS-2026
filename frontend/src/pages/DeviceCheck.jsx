import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mic, Camera, CameraOff, ArrowRight } from 'lucide-react';
import { Button } from '../components/Button.jsx';
import { PageHeading } from '../components/PageHeading.jsx';
import { current, lessonUrl } from '../lib/lesson.js';
import { device } from '../lib/device.js';

export function DeviceCheck() {
    const navigate = useNavigate();
    const [config] = useState(current);
    const [mic, setMic] = useState(() =>
        device.stream?.getAudioTracks().some((t) => t.readyState === 'live') ? 'ready' : 'idle',
    );
    const [camera, setCamera] = useState(() =>
        device.stream?.getVideoTracks().some((t) => t.readyState === 'live') ? 'ready' : 'off',
    );
    const [message, setMessage] = useState('');
    const video = useRef(null);
    useEffect(() => {
        if (video.current && device.stream) video.current.srcObject = device.stream;
        return () => {};
    }, [camera]);
    async function requestMic() {
        setMic('checking');
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: true,
            });
            device.stream?.getAudioTracks().forEach((t) => {
                t.stop();
                device.stream?.removeTrack(t);
            });
            if (device.stream) stream.getAudioTracks().forEach((t) => device.stream?.addTrack(t));
            else device.stream = stream;
            setMic('ready');
            setMessage('Mikrofon siap.');
        } catch {
            setMic('denied');
            setMessage('Akses mikrofon ditolak. Izinkan mikrofon pada pengaturan situs, lalu coba lagi.');
        }
    }
    async function requestCamera() {
        setCamera('checking');
        try {
            const cam = await navigator.mediaDevices.getUserMedia({
                video: true,
            });
            if (device.stream) {
                cam.getVideoTracks().forEach((t) => device.stream?.addTrack(t));
            } else device.stream = cam;
            setCamera('ready');
            setMessage('Kamera aktif.');
        } catch {
            setCamera('denied');
            setMessage('Kamera tidak tersedia. Anda tetap dapat berlatih hanya dengan audio.');
        }
    }
    function offCamera() {
        device.stream?.getVideoTracks().forEach((t) => {
            t.stop();
            device.stream?.removeTrack(t);
        });
        setCamera('off');
    }
    function begin() {
        if (mic !== 'ready' || !device.stream?.getAudioTracks().some((t) => t.readyState === 'live')) {
            setMic('idle');
            setMessage('Mikrofon terputus. Periksa lagi sebelum masuk.');
            return;
        }
        device.stream.getAudioTracks().forEach((t) => (t.enabled = true));
        sessionStorage.setItem('gema-camera', String(camera === 'ready'));
        navigate('/simulator/room');
    }
    return (
        <div className="page flow-page">
            <div className="flow-steps">
                <span className="done">
                    <i aria-hidden>1</i>
                    <b>Persiapan</b>
                </span>
                <span className="active" aria-current="step">
                    <i aria-hidden>2</i>
                    <b>Perangkat</b>
                </span>
                <span>
                    <i aria-hidden>3</i>
                    <b>Ruang latihan</b>
                </span>
                <span>
                    <i aria-hidden>4</i>
                    <b>Refleksi</b>
                </span>
            </div>
            <PageHeading
                title="Periksa perangkat Anda"
                description={`${config.lesson.subject} · ${config.lesson.chapter} · ${config.lesson.kelas}`}
            />
            <div className="device-layout">
                <section className="camera-preview card">
                    {camera === 'ready' ? (
                        <video autoPlay muted playsInline ref={video} aria-label="Pratinjau kamera Anda" />
                    ) : (
                        <div className="preview-placeholder">
                            <CameraOff size={34} />
                            <strong>Kamera belum aktif</strong>
                            <span>Latihan audio saja tetap bisa dilakukan</span>
                        </div>
                    )}
                    <span className="preview-label">Pratinjau Anda</span>
                </section>
                <div className="device-panel card">
                    <div className="device-item">
                        <span className="device-icon">
                            <Mic size={22} />
                        </span>
                        <span>
                            <strong>
                                {'Mikrofon '}
                                <em>Wajib</em>
                            </strong>
                            <small>
                                {mic === 'ready'
                                    ? 'Siap digunakan'
                                    : mic === 'denied'
                                      ? 'Akses ditolak'
                                      : 'Belum diperiksa'}
                            </small>
                        </span>
                        <Button
                            onClick={requestMic}
                            disabled={mic === 'checking'}
                            variant={mic === 'ready' ? 'subtle' : 'secondary'}
                        >
                            {mic === 'ready' ? 'Periksa lagi' : 'Izinkan'}
                        </Button>
                    </div>
                    <div className="device-item">
                        <span className="device-icon">
                            <Camera size={22} />
                        </span>
                        <span>
                            <strong>
                                {'Kamera '}
                                <em>Opsional</em>
                            </strong>
                            <small>
                                {camera === 'ready'
                                    ? 'Pratinjau aktif'
                                    : camera === 'denied'
                                      ? 'Tidak diizinkan'
                                      : 'Anda bisa lanjut tanpa kamera'}
                            </small>
                        </span>
                        {camera === 'ready' ? (
                            <Button onClick={offCamera} variant="subtle">
                                Matikan
                            </Button>
                        ) : (
                            <Button onClick={requestCamera} disabled={camera === 'checking'} variant="secondary">
                                Aktifkan
                            </Button>
                        )}
                    </div>
                    {message && (
                        <div className={`notice ${mic === 'denied' ? 'error' : 'neutral'}`} role="status">
                            {message}
                        </div>
                    )}
                    <div className="device-actions">
                        <Button
                            to={lessonUrl(config.lesson, config.scheduleId ?? undefined)}
                            state={{ resume: true }}
                            variant="subtle"
                        >
                            Kembali
                        </Button>
                        <Button onClick={begin} disabled={mic !== 'ready'} icon={ArrowRight}>
                            Masuk ruang latihan
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
