// The Room's main stage: the topic card, one of the lesson's items (a PDF or a picture), or a shared screen.
//
// Nothing is shown until the teacher picks it: "Pilih materi" opens a list of the lesson's items, plus
// "Bagikan layar" and "Tampilkan topik". Every change of what is on show is reported with `onStage(page)` in the
// bundle's page numbers (docs/api-contract.md): a PDF page or a picture's page, or 0 when no slide text is on show
// (the topic card or a shared screen). The last page of each PDF is remembered when the teacher switches away.
import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { FileText, Image as ImageIcon, Layers, ScreenShare, Sparkles, X } from 'lucide-react';
import { materialFileContentUrl } from './api.js';
import ImageStage from './ImageStage.jsx';
import ShareStage from './ShareStage.jsx';

const PdfStage = lazy(() => import('./PdfStage.jsx')); // pdf.js is downloaded only when a PDF is shown

/**
 * `initial` and `onStateChange` carry { shownId, pdfPages } so a resumed lesson comes back where it was.
 */
export default function StageArea({ files, sharing, shareStream, canShare, onStartShare, onStopShare, onStage, topicCard, initial, onStateChange }) {
    const [shownId, setShownId] = useState(initial?.shownId ?? null);
    const [pdfPages, setPdfPages] = useState(initial?.pdfPages ?? {}); // file id -> page within that PDF
    const [picking, setPicking] = useState(false);
    const shown = files.find((f) => f.id === shownId) ?? null;
    const report = useRef(onStage);
    report.current = onStage;

    useEffect(() => onStateChange?.({ shownId, pdfPages }), [shownId, pdfPages]);

    const pageNow = () => (!shown ? 0 : shown.kind === 'pdf' ? shown.first_page + (pdfPages[shown.id] ?? 1) - 1 : shown.first_page);

    // when sharing stops, what was on the stage before is on show again
    const wasSharing = useRef(sharing);
    useEffect(() => {
        if (wasSharing.current && !sharing && files.length)
            report.current(pageNow());
        wasSharing.current = sharing;
    }, [sharing]);

    function show(file) {
        setPicking(false);
        if (sharing) { // picking ends the share; the effect above then reports what is on show
            onStopShare();
            setShownId(file?.id ?? null);
            return;
        }
        if (file?.id === shownId)
            return;
        setShownId(file?.id ?? null);
        if (!file)
            report.current(0);
        else if (file.kind === 'image')
            report.current(file.first_page);
        // a PDF reports its page itself once it has loaded (PdfStage calls onPageChange)
    }

    function share() {
        setPicking(false);
        onStartShare();
    }

    // Escape closes the list
    useEffect(() => {
        if (!picking)
            return;
        const close = (e) => e.key === 'Escape' && setPicking(false);
        window.addEventListener('keydown', close);
        return () => window.removeEventListener('keydown', close);
    }, [picking]);

    const label = sharing ? 'Layar yang dibagikan' : shown ? shown.filename : 'Topik pelajaran';
    return (<>
        {(files.length > 0 || canShare) && <div className="stage-switch">
            <span className="stage-switch-label" title={label}>{label}</span>
            <button type="button" className="stage-switch-button" onClick={() => setPicking(true)} aria-haspopup="dialog">
                <Layers size={16} />
                <span>{shown || sharing ? 'Ganti materi' : 'Pilih materi'}</span>
            </button>
        </div>}

        {sharing && <ShareStage stream={shareStream} onStop={onStopShare} />}
        {shown?.kind === 'pdf' && <div className="stage-center has-pdf" style={sharing ? { display: 'none' } : undefined}>
            <Suspense fallback={<p role="status">Memuat materi…</p>}>
                <PdfStage key={shown.id} url={materialFileContentUrl(shown.id)} name={shown.filename}
                    initialPage={pdfPages[shown.id] ?? 1} active={!sharing && !picking}
                    onPageChange={(n) => {
                        setPdfPages((old) => ({ ...old, [shown.id]: n }));
                        report.current(shown.first_page + n - 1);
                    }} />
            </Suspense>
        </div>}
        {shown?.kind === 'image' && !sharing && <div className="stage-center has-pdf"><ImageStage file={shown} /></div>}
        {!shown && !sharing && topicCard}

        {picking && <div className="stage-picker-backdrop" onClick={() => setPicking(false)}>
            <div className="stage-picker" role="dialog" aria-modal="true" aria-labelledby="stage-picker-title" onClick={(e) => e.stopPropagation()}>
                <div className="stage-picker-head">
                    <strong id="stage-picker-title">Tampilkan di layar utama</strong>
                    <button type="button" className="icon-button" onClick={() => setPicking(false)} aria-label="Tutup"><X size={16} /></button>
                </div>
                <ul>
                    {files.map((file) => <li key={file.id}>
                        <button type="button" className={file.id === shownId && !sharing ? 'current' : ''} onClick={() => show(file)} autoFocus={file.id === shownId}>
                            {file.kind === 'pdf' ? <FileText size={18} /> : <ImageIcon size={18} />}
                            <span>
                                <strong>{file.filename}</strong>
                                <small>{file.kind === 'pdf' ? `PDF · ${file.page_count} halaman${pdfPages[file.id] ? ` · terakhir di halaman ${pdfPages[file.id]}` : ''}` : 'Gambar'}</small>
                            </span>
                        </button>
                    </li>)}
                    {canShare && <li>
                        <button type="button" className={sharing ? 'current' : ''} onClick={share}>
                            <ScreenShare size={18} />
                            <span><strong>Bagikan layar</strong><small>Jendela, tab, atau seluruh layar. Hanya tampil di sini.</small></span>
                        </button>
                    </li>}
                    <li>
                        <button type="button" className={!shown && !sharing ? 'current' : ''} onClick={() => show(null)}>
                            <Sparkles size={18} />
                            <span><strong>Tampilkan topik</strong><small>Tanpa materi di layar</small></span>
                        </button>
                    </li>
                </ul>
            </div>
        </div>}
    </>);
}
