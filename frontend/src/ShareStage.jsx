// Mode B of screen sharing: the teacher's own screen, window or tab drawn on the stage.
//
// The picture comes from the browser's screen-share picker and goes into a <video> element, nothing else:
// it is never drawn to a canvas that is read, never recorded and never sent anywhere. No frame reaches the backend.
import { useEffect, useRef } from 'react';
import { ScreenShare, ScreenShareOff } from 'lucide-react';

export default function ShareStage({ stream, onStop }) {
    const video = useRef(null);
    useEffect(() => {
        const element = video.current;
        if (element)
            element.srcObject = stream;
        return () => {
            if (element)
                element.srcObject = null;
        };
    }, [stream]);
    return (<div className="stage-center has-pdf share-stage">
        <div className="share-banner" role="status">
            <ScreenShare size={16} />
            <span>Anda sedang berbagi layar. Gambar hanya tampil di sini dan tidak diunggah.</span>
        </div>
        <div className="share-video-holder">
            <video ref={video} autoPlay muted playsInline aria-label="Layar yang Anda bagikan" />
        </div>
        <div className="pdf-controls">
            <button type="button" className="share-stop" onClick={onStop}>
                <ScreenShareOff size={17} />
                <span>Berhenti berbagi</span>
            </button>
        </div>
    </div>);
}
