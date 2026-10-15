// Setup: the items a teacher brings to a lesson (PDFs, JPEG/PNG pictures), uploaded one at a time.
//
// The server is the authority on limits; the same limits are checked here first so a teacher does not wait for an
// upload that would be refused. Pictures are read for text on the server in the background; their status is polled.
import { useEffect, useRef, useState } from 'react';
import { CircleCheck, FileText, Image as ImageIcon, LoaderCircle, Upload, X, AlertCircle } from 'lucide-react';
import * as api from '../../lib/api.js';

const MB = 1024 * 1024;
const DEFAULT_LIMITS = { files: 10, bytes: 50 * MB, pdf_bytes: 20 * MB, image_bytes: 8 * MB, pdf_pages: 300 };
const POLL_MS = 2500;
const ACCEPT = 'application/pdf,.pdf,image/jpeg,.jpg,.jpeg,image/png,.png';

const kindOf = (file) => {
    const name = file.name.toLowerCase();
    if (file.type === 'application/pdf' || name.endsWith('.pdf')) return 'pdf';
    if (['image/jpeg', 'image/png'].includes(file.type) || /\.(jpe?g|png)$/.test(name)) return 'image';
    return null;
};
const size = (bytes) =>
    bytes < MB ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / MB).toFixed(1).replace('.', ',')} MB`;

/**
 * `value` is { materialId, files, busy }: `files` are the server's MaterialFile items, `busy` is true while
 * something is still uploading. `onChange` receives the next value.
 */
export default function MaterialUploader({ value, onChange }) {
    const [rows, setRows] = useState(() =>
        (value.files ?? []).map((file) => ({ key: file.id, name: file.filename, file })),
    );
    const [usage, setUsage] = useState(null);
    const [limits, setLimits] = useState(DEFAULT_LIMITS);
    const [message, setMessage] = useState('');
    const [dragging, setDragging] = useState(false);
    const materialId = useRef(value.materialId ?? null);
    const queue = useRef(Promise.resolve());
    const latest = useRef(rows);
    latest.current = rows;

    // tell Setup what is uploaded, and whether anything is still on its way
    useEffect(() => {
        onChange({
            materialId: materialId.current,
            files: rows.filter((r) => r.file).map((r) => r.file),
            busy: rows.some((r) => r.state === 'uploading'),
        });
    }, [rows]);

    // pictures are read on the server; ask again until none is still being read
    const reading = rows.some((r) => r.file?.status === 'reading');
    useEffect(() => {
        if (!reading || !materialId.current) return;
        const timer = setInterval(refresh, POLL_MS);
        return () => clearInterval(timer);
    }, [reading]);

    async function refresh() {
        if (!materialId.current) return;
        try {
            const listed = await api.listMaterialFiles(materialId.current);
            setUsage(listed.used);
            setLimits(listed.limits);
            const byId = new Map(listed.files.map((f) => [f.id, f]));
            setRows((prev) =>
                prev.map((r) => (r.file && byId.has(r.file.id) ? { ...r, file: byId.get(r.file.id) } : r)),
            );
        } catch {
            /* the next poll tries again */
        }
    }

    function pending() {
        const kept = latest.current.filter((r) => r.file || r.state === 'uploading');
        return {
            count: kept.length,
            bytes: kept.reduce((n, r) => n + (r.file?.size_bytes ?? r.size ?? 0), 0),
        };
    }

    function add(list) {
        setMessage('');
        for (const file of list) {
            const kind = kindOf(file);
            const key = `${file.name}-${file.size}-${Math.random().toString(36).slice(2)}`;
            const { count, bytes } = pending();
            let problem = '';
            if (!kind) problem = 'Berkas harus berupa PDF, JPG, atau PNG.';
            else if (file.size === 0) problem = 'Berkas ini kosong.';
            else if (kind === 'pdf' && file.size > limits.pdf_bytes)
                problem = `PDF lebih dari ${limits.pdf_bytes / MB} MB.`;
            else if (kind === 'image' && file.size > limits.image_bytes)
                problem = `Gambar lebih dari ${limits.image_bytes / MB} MB.`;
            else if (count + 1 > limits.files)
                problem = `Satu pelajaran bisa memuat paling banyak ${limits.files} berkas.`;
            else if (bytes + file.size > limits.bytes)
                problem = `Total materi satu pelajaran paling banyak ${limits.bytes / MB} MB.`;
            const row = {
                key,
                name: file.name,
                size: file.size,
                kind,
                state: problem ? 'error' : 'uploading',
                error: problem,
            };
            latest.current = [...latest.current, row];
            setRows((prev) => [...prev, row]);
            if (!problem) queue.current = queue.current.then(() => upload(key, file)); // one upload at a time
        }
    }

    async function upload(key, file) {
        const update = (patch) => setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));
        try {
            if (!materialId.current) materialId.current = (await api.createMaterial()).id;
            const uploaded = await api.uploadMaterialFile(materialId.current, file);
            update({ state: 'done', file: uploaded });
            refresh();
        } catch (err) {
            update({ state: 'error', error: err.message });
        }
    }

    async function remove(row) {
        if (row.state === 'uploading') return;
        if (row.file) {
            try {
                await api.deleteMaterialFile(materialId.current, row.file.id);
            } catch (err) {
                const gone = err instanceof api.ApiError && (err.status === 404 || err.status === 409);
                if (!gone) {
                    setMessage(err.message);
                    return;
                }
            }
        }
        setRows((prev) => prev.filter((r) => r.key !== row.key));
        refresh();
    }

    const used = usage ?? {
        files: rows.filter((r) => r.file).length,
        bytes: rows.reduce((n, r) => n + (r.file?.size_bytes ?? 0), 0),
    };
    return (
        <div
            className={`upload-block ${dragging ? 'dragging' : ''}`}
            onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                add([...e.dataTransfer.files]);
            }}
        >
            <div>
                <Upload size={21} />
                <strong>
                    Materi pendukung <span className="muted">(opsional)</span>
                </strong>
            </div>
            <p>
                PDF, JPG, atau PNG, boleh lebih dari satu. Saat mengajar, Anda memilih materi mana yang ditampilkan.
                Berkas diunggah ke server lokal di laptop Anda; teks pada gambar dibaca agar pertanyaan murid sesuai isi
                materi.
            </p>
            <label className="file-button">
                Pilih berkas
                <input
                    type="file"
                    accept={ACCEPT}
                    multiple
                    onChange={(e) => {
                        add([...e.target.files]);
                        e.target.value = '';
                    }}
                />
            </label>
            <span className="upload-hint">atau seret berkas ke sini</span>
            {rows.length > 0 && (
                <ul className="material-list" aria-live="polite">
                    {rows.map((row) => (
                        <MaterialRow key={row.key} row={row} onRemove={() => remove(row)} />
                    ))}
                </ul>
            )}
            <span className="upload-usage">
                {used.files} dari {limits.files} berkas · {size(used.bytes)} dari {limits.bytes / MB} MB · PDF maks.{' '}
                {limits.pdf_bytes / MB} MB, gambar maks. {limits.image_bytes / MB} MB
            </span>
            {message && (
                <span className="error-text" role="alert">
                    {message}
                </span>
            )}
        </div>
    );
}

function MaterialRow({ row, onRemove }) {
    const file = row.file;
    const kind = file?.kind ?? row.kind;
    let state;
    if (row.state === 'error')
        state = (
            <span className="material-state error">
                <AlertCircle size={14} />
                {row.error}
            </span>
        );
    else if (row.state === 'uploading')
        state = (
            <span className="material-state">
                <LoaderCircle size={14} className="spin" />
                Mengunggah…
            </span>
        );
    else if (file.status === 'reading')
        state = (
            <span className="material-state">
                <LoaderCircle size={14} className="spin" />
                {file.status_text}
            </span>
        );
    else if (file.status === 'ready')
        state = (
            <span className="material-state ok">
                <CircleCheck size={14} />
                Siap{file.kind === 'pdf' ? ` · ${file.page_count} halaman` : ''}
            </span>
        );
    else
        state = (
            <span className="material-state warn">
                <AlertCircle size={14} />
                {file.status_text}
            </span>
        );
    return (
        <li className="material-row">
            {kind === 'image' ? <ImageIcon size={18} /> : <FileText size={18} />}
            <span className="material-name">
                <strong title={row.name}>{row.name}</strong>
                {state}
            </span>
            <button
                type="button"
                className="icon-button"
                onClick={onRemove}
                disabled={row.state === 'uploading'}
                aria-label={`Hapus ${row.name}`}
            >
                <X size={16} />
            </button>
        </li>
    );
}
