// Mode A of screen sharing: the teacher's PDF drawn on the stage, one page at a time.
//
// Efficiency: only the page on screen is drawn, and only when it changes or the stage is resized; the next page is
// parsed in the background so a turn feels instant; older pages are released. pdf.js decodes in a web worker, so the
// room and the microphone recorder never wait for it. The file is fetched in pieces (HTTP Range), so page 1 shows
// before a large PDF has fully arrived. This module is loaded lazily: lessons without a PDF never download pdf.js.
//
// Privacy: pages are drawn to a canvas only. Nothing here is sent anywhere; the room is told which page is showing.
import { useCallback, useEffect, useRef, useState } from 'react';
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs'; // the legacy build also runs on older browsers
import workerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { authHeaders } from './api.js';

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

const MAX_DPR = 2; // sharper than this is invisible but costs memory
const MAX_PIXELS = 3_000_000; // cap on one drawn page, so a huge page cannot exhaust a weak laptop
const RESIZE_DELAY_MS = 150;

const typing = (el) => el && (['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName) || el.isContentEditable);

// `url` is the PDF to show; pages are numbered from 1 within it, and `onPageChange` receives those numbers.
// `active` is false while the stage shows a shared screen instead: the viewer stays loaded, but ignores the keys.
export default function PdfStage({ url, name, initialPage = 1, onPageChange, active = true }) {
    const [pdf, setPdf] = useState(null);
    const [status, setStatus] = useState('loading'); // loading | ready | error
    const [page, setPage] = useState(initialPage);
    const [box, setBox] = useState({ w: 0, h: 0 });
    const holder = useRef(null);
    const canvas = useRef(null);
    const pages = useRef(new Map()); // page number -> loaded pdf.js page, so only a few stay in memory
    const report = useRef(onPageChange);
    report.current = onPageChange;
    const total = pdf?.numPages ?? 0;

    // Load the document once.
    useEffect(() => {
        let gone = false;
        const task = pdfjs.getDocument({
            url,
            httpHeaders: authHeaders(),
            isEvalSupported: false, // no code generated from the file
            disableAutoFetch: true, // fetch what is shown, not the whole file in the background
            rangeChunkSize: 262144,
        });
        task.promise.then((doc) => {
            if (gone)
                return;
            const first = Math.min(Math.max(1, initialPage), doc.numPages);
            setPdf(doc);
            setPage(first);
            setStatus('ready');
            report.current?.(first); // "once for page 1 at start"
        }, () => {
            if (!gone)
                setStatus('error');
        });
        return () => {
            gone = true;
            pages.current.clear();
            task.destroy();
        };
    }, [url]);

    // Follow the size of the stage.
    useEffect(() => {
        if (!holder.current)
            return;
        let timer;
        const measure = () => {
            const { width, height } = holder.current.getBoundingClientRect();
            setBox((old) => (Math.abs(old.w - width) < 2 && Math.abs(old.h - height) < 2 ? old : { w: width, h: height }));
        };
        measure();
        const observer = new ResizeObserver(() => {
            clearTimeout(timer);
            timer = setTimeout(measure, RESIZE_DELAY_MS);
        });
        observer.observe(holder.current);
        return () => {
            clearTimeout(timer);
            observer.disconnect();
        };
    }, [status]);

    // Draw the page on screen. Drawn off screen first and then copied, so a page turn never flashes blank.
    useEffect(() => {
        if (!pdf || !box.w || !box.h || !canvas.current)
            return;
        let cancelled = false, task = null;
        (async () => {
            const current = pages.current.get(page) ?? await pdf.getPage(page);
            pages.current.set(page, current);
            if (cancelled)
                return;
            const natural = current.getViewport({ scale: 1 });
            const fit = Math.min(box.w / natural.width, box.h / natural.height);
            let ratio = Math.min(window.devicePixelRatio || 1, MAX_DPR);
            const pixels = natural.width * fit * ratio * natural.height * fit * ratio;
            if (pixels > MAX_PIXELS)
                ratio *= Math.sqrt(MAX_PIXELS / pixels);
            const viewport = current.getViewport({ scale: fit * ratio });
            const off = document.createElement('canvas');
            off.width = Math.floor(viewport.width);
            off.height = Math.floor(viewport.height);
            task = current.render({ canvasContext: off.getContext('2d', { alpha: false }), viewport, background: '#ffffff' });
            await task.promise;
            if (cancelled)
                return;
            const shown = canvas.current;
            shown.width = off.width;
            shown.height = off.height;
            shown.style.width = `${Math.floor(viewport.width / ratio)}px`;
            shown.style.height = `${Math.floor(viewport.height / ratio)}px`;
            shown.getContext('2d').drawImage(off, 0, 0);
            off.width = off.height = 0; // free the off-screen bitmap now
            // get the next page ready, and let go of the ones no longer needed
            if (page < pdf.numPages && !pages.current.has(page + 1))
                pdf.getPage(page + 1).then((next) => !cancelled && pages.current.set(page + 1, next), () => { });
            for (const [n, old] of pages.current)
                if (n !== page && n !== page + 1) {
                    old.cleanup();
                    pages.current.delete(n);
                }
        })().catch((err) => {
            if (!cancelled && err?.name !== 'RenderingCancelledException')
                setStatus('error');
        });
        return () => {
            cancelled = true;
            task?.cancel();
        };
    }, [pdf, page, box]);

    const go = useCallback((n) => {
        if (!total)
            return;
        const next = Math.min(Math.max(1, n), total);
        if (next === page)
            return;
        setPage(next);
        report.current?.(next);
    }, [page, total]);

    // Arrow keys and PageUp/PageDown, unless the teacher is typing or a dialog is open.
    useEffect(() => {
        const onKey = (e) => {
            if (!active || e.repeat || e.altKey || e.ctrlKey || e.metaKey || typing(document.activeElement) || document.querySelector('[role="dialog"],[role="alertdialog"]'))
                return;
            if (e.key === 'ArrowRight' || e.key === 'PageDown')
                go(page + 1);
            else if (e.key === 'ArrowLeft' || e.key === 'PageUp')
                go(page - 1);
            else
                return;
            e.preventDefault();
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [go, page, active]);

    if (status === 'error')
        return (<div className="pdf-stage pdf-message" role="status">
            <strong>Materi belum bisa ditampilkan.</strong>
            <span>Latihan tetap bisa dilanjutkan tanpa materi di layar.</span>
        </div>);
    return (<div className="pdf-stage">
        <div className="pdf-canvas-holder" ref={holder}>
            {status === 'loading' && <span className="pdf-message" role="status">Memuat materi…</span>}
            <canvas ref={canvas} role="img" aria-label={`Halaman ${page} dari ${total} · ${name ?? 'materi'}`} />
        </div>
        {status === 'ready' && <div className="pdf-controls">
            <button type="button" className="icon-button" onClick={() => go(page - 1)} disabled={page <= 1} aria-label="Halaman sebelumnya">
                <ChevronLeft size={20} />
            </button>
            <span aria-live="polite">Halaman {page} dari {total}</span>
            <button type="button" className="icon-button" onClick={() => go(page + 1)} disabled={page >= total} aria-label="Halaman berikutnya">
                <ChevronRight size={20} />
            </button>
        </div>}
    </div>);
}
