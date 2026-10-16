import { useEffect, useRef, useState } from 'react';
import { CameraOff, ShieldCheck, Maximize2 } from 'lucide-react';
import StageArea from '../stage/StageArea.jsx';

// The teacher's own picture: small leaves the most room for the slide, large is easiest to see oneself.
const CAMERA_SIZES = ['kecil', 'sedang', 'besar'];
const SIZE_KEY = 'baskom-camera-size';
// A small shield on the camera picture instead of a line of text: the reassurance is there when the teacher wants it.
function SecureBadge() {
    const [hover, setHover] = useState(false);
    const [pinned, setPinned] = useState(false); // a tap or key press keeps it open (touch screens have no hover)
    const wrap = useRef(null);
    const open = hover || pinned;
    useEffect(() => {
        if (!pinned) return;
        const close = (e) => {
            if (e.type === 'keydown' ? e.key === 'Escape' : !wrap.current?.contains(e.target)) setPinned(false);
        };
        window.addEventListener('keydown', close);
        window.addEventListener('pointerdown', close);
        return () => {
            window.removeEventListener('keydown', close);
            window.removeEventListener('pointerdown', close);
        };
    }, [pinned]);
    return (
        <div
            className="secure-badge"
            ref={wrap}
            onMouseEnter={() => setHover(true)}
            onMouseLeave={() => setHover(false)}
        >
            <button
                type="button"
                aria-expanded={open}
                aria-describedby="secure-note"
                aria-label="Privasi video Anda"
                onClick={() => setPinned((v) => !v)}
                onFocus={() => setHover(true)}
                onBlur={() => setHover(false)}
            >
                <ShieldCheck size={16} />
            </button>
            <p id="secure-note" role="tooltip" hidden={!open}>
                Aman: video dan layar Anda hanya tampil di perangkat ini dan tidak pernah diunggah. Yang dikirim hanya
                potongan suara dan angka ringkas.
            </p>
        </div>
    );
}

const readSize = () => {
    try {
        const saved = localStorage.getItem(SIZE_KEY);
        return CAMERA_SIZES.includes(saved) ? saved : 'sedang';
    } catch {
        return 'sedang';
    }
};

export function LessonStage({
    lesson,
    hasMaterial,
    files,
    sharing,
    shareStream,
    canShare,
    onStartShare,
    onStopShare,
    onStage,
    stageState,
    onStageStateChange,
    paused,
    offline,
    camera,
    videoRef,
}) {
    const [cameraSize, setCameraSize] = useState(readSize);
    function nextSize() {
        const next = CAMERA_SIZES[(CAMERA_SIZES.indexOf(cameraSize) + 1) % CAMERA_SIZES.length];
        setCameraSize(next);
        try {
            localStorage.setItem(SIZE_KEY, next);
        } catch {
            /* the choice only lasts for this visit */
        }
    }
    return (
        <section className={`lesson-stage ${files.length || sharing ? 'has-pdf' : ''}`}>
            <div className="stage-top">
                <span className="stage-indicator">
                    {paused ? 'Dijeda' : offline ? 'Menunggu koneksi' : 'Latihan aktif'}
                </span>
            </div>
            <StageArea
                files={files}
                sharing={sharing}
                shareStream={shareStream}
                canShare={canShare}
                onStartShare={onStartShare}
                onStopShare={onStopShare}
                onStage={(page) => hasMaterial && onStage(page)}
                initial={stageState}
                onStateChange={onStageStateChange}
                topicCard={
                    <div className="stage-center">
                        <span className="stage-label">Topik hari ini</span>
                        <h1>{lesson.chapter}</h1>
                        <p>{lesson.subchapter}</p>
                        <span className="stage-subject">
                            {lesson.subject}
                            {' · '}
                            {lesson.kelas}
                        </span>
                        {files.length > 0 && (
                            <p className="material-caption">
                                {files.length}
                                {' materi siap. Pilih yang ingin ditampilkan dengan tombol Pilih materi.'}
                            </p>
                        )}
                    </div>
                }
            />
            <div className="stage-side">
                <div className="self-wrap">
                    <div className={`self-view self-view-${cameraSize}`}>
                        {camera ? (
                            <video autoPlay muted playsInline ref={videoRef} aria-label="Video diri Anda" />
                        ) : (
                            <div>
                                <CameraOff size={21} />
                                <small>Kamera nonaktif</small>
                            </div>
                        )}
                        <span>Anda</span>
                        <button
                            type="button"
                            className="self-view-size"
                            onClick={nextSize}
                            aria-label={`Ukuran kamera: ${cameraSize}. Tekan untuk mengubah.`}
                            title={`Ukuran kamera: ${cameraSize}`}
                        >
                            <Maximize2 size={14} />
                        </button>
                    </div>
                    <SecureBadge />
                </div>
            </div>
        </section>
    );
}
