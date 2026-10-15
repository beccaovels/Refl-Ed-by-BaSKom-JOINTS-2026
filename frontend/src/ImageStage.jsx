// A picture the teacher brought (JPEG/PNG), fitted to the stage.
//
// An <img src> cannot send the X-User-Id header, so the picture is fetched with it and shown from a blob URL,
// released again when the stage moves on. Nothing is sent anywhere; the room logs which page is on show.
import { useEffect, useState } from 'react';
import { authHeaders, materialFileContentUrl } from './api.js';

export default function ImageStage({ file }) {
    const [src, setSrc] = useState(null);
    const [failed, setFailed] = useState(false);

    useEffect(() => {
        let url = null, gone = false;
        setSrc(null);
        setFailed(false);
        fetch(materialFileContentUrl(file.id), { headers: authHeaders() })
            .then((r) => (r.ok ? r.blob() : Promise.reject(new Error(String(r.status)))))
            .then((blob) => {
                if (gone)
                    return;
                url = URL.createObjectURL(blob);
                setSrc(url);
            })
            .catch(() => !gone && setFailed(true));
        return () => {
            gone = true;
            if (url)
                URL.revokeObjectURL(url);
        };
    }, [file.id]);

    if (failed)
        return (<div className="pdf-stage pdf-message" role="status">
            <strong>Gambar belum bisa ditampilkan.</strong>
            <span>Latihan tetap bisa dilanjutkan; pilih materi lain atau tampilkan topik.</span>
        </div>);
    return (<div className="pdf-stage">
        <div className="pdf-canvas-holder">
            {src ? <img className="stage-image" src={src} alt={file.filename} /> : <span className="pdf-message" role="status">Memuat gambar…</span>}
        </div>
        {['unreadable', 'failed'].includes(file.status) && <p className="stage-note">{file.status_text}</p>}
    </div>);
}
