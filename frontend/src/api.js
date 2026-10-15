// The only place that talks to the backend. See docs/api-contract.md.
// In development Vite forwards /api to http://localhost:8000 (vite.config.js), so there is no CORS to set up.
const BASE = import.meta.env?.VITE_API_URL ?? '/api';
const USER_KEY = 'baskom-user';

export class ApiError extends Error {
    constructor(status, detail) {
        super(detail);
        this.status = status;
    }
}

// --- demo login: type a name, no password. The backend only needs to know which teacher this is. ---
export function getUser() {
    try {
        return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
    }
    catch {
        return null;
    }
}
export function logout() {
    try {
        localStorage.removeItem(USER_KEY);
    }
    catch { /* nothing to clear */ }
}
export async function login(name) {
    const clean = name.trim();
    const slug = clean.toLowerCase().normalize('NFD').replace(/[^a-z0-9]+/g, '.').replace(/^\.+|\.+$/g, '') || 'guru';
    const { data } = await call('/auth/login', { method: 'POST', json: { name: clean, email: `${slug}@demo.local` }, auth: false });
    try {
        localStorage.setItem(USER_KEY, JSON.stringify(data));
    }
    catch { /* the user can still work this visit */ }
    return data;
}

async function call(path, { method = 'GET', json, form, auth = true } = {}) {
    const headers = {};
    if (auth) {
        const user = getUser();
        if (user)
            headers['X-User-Id'] = user.id;
    }
    if (json !== undefined)
        headers['Content-Type'] = 'application/json';
    let response;
    try {
        response = await fetch(BASE + path, { method, headers, body: json !== undefined ? JSON.stringify(json) : form });
    }
    catch {
        throw new ApiError(0, 'Server tidak bisa dihubungi. Pastikan backend berjalan.');
    }
    const text = await response.text();
    let data = null;
    try {
        data = text ? JSON.parse(text) : null;
    }
    catch { /* not JSON */ }
    if (!response.ok) {
        // a validation error (422) lists the fields that failed: name the first one
        const first = Array.isArray(data?.detail) ? data.detail[0] : null;
        const detail = typeof data?.detail === 'string' ? data.detail
            : first ? `Permintaan gagal (${response.status}): ${first.loc?.slice(1).join('.')} ${first.msg}`
                : `Permintaan gagal (${response.status}).`;
        throw new ApiError(response.status, detail);
    }
    return { status: response.status, data };
}

/** Where pdf.js fetches the teacher's PDF from, and the header it must send (it does its own requests). */
export const materialFileUrl = (materialId) => `${BASE}/materials/${materialId}/file`;
export const authHeaders = () => {
    const user = getUser();
    return user ? { 'X-User-Id': user.id } : {};
};

export const profiles = async () => (await call('/profiles')).data;
export async function uploadMaterial(file) {
    const form = new FormData();
    form.append('file', file);
    return (await call('/materials', { method: 'POST', form })).data;
}
// A lesson's material is a bundle of items (PDFs, JPEG/PNG pictures); see Materials in docs/api-contract.md.
export const createMaterial = async () => (await call('/materials', { method: 'POST' })).data;
export async function uploadMaterialFile(materialId, file) {
    const form = new FormData();
    form.append('file', file);
    return (await call(`/materials/${materialId}/files`, { method: 'POST', form })).data;
}
export const listMaterialFiles = async (materialId) => (await call(`/materials/${materialId}/files`)).data;
export const deleteMaterialFile = (materialId, fileId) => call(`/materials/${materialId}/files/${fileId}`, { method: 'DELETE' });
/** Where an item is fetched from for the stage (pdf.js, or a picture fetched with authHeaders). */
export const materialFileContentUrl = (fileId) => `${BASE}/files/${fileId}/content`;
export const createSession = async (body) => (await call('/sessions', { method: 'POST', json: body })).data;
export const sendSlide = (sessionId, page, t_ms) => call(`/sessions/${sessionId}/slides`, { method: 'POST', json: { page, t_ms } });
export async function sendAudio(sessionId, seq, start_ms, end_ms, wav) {
    const form = new FormData();
    form.append('seq', String(seq));
    form.append('start_ms', String(start_ms));
    form.append('end_ms', String(end_ms));
    form.append('file', wav, 'piece.wav');
    return (await call(`/sessions/${sessionId}/audio`, { method: 'POST', form })).data;
}
export const endLesson = async (sessionId) => (await call(`/sessions/${sessionId}/end`, { method: 'POST' })).data.event;
export const finishLesson = (sessionId) => call(`/sessions/${sessionId}/finish`, { method: 'POST' });
/** `{ status: 200, data: report }` when ready, `{ status: 202 }` while it is being made. */
export const getReport = (sessionId) => call(`/sessions/${sessionId}/report`);
export const flagItem = (reportId, itemId) => call(`/reports/${reportId}/flags`, { method: 'POST', json: { item_id: itemId } });

/** Start the report and wait for it (it takes 10-40 s). Calling /finish again is safe, so a restart in between is recovered. */
export async function waitForReport(sessionId, { everyMs = 2000, giveUpMs = 180000 } = {}) {
    await finishLesson(sessionId);
    const deadline = Date.now() + giveUpMs;
    let restarted = false;
    while (Date.now() < deadline) {
        try {
            const { status, data } = await getReport(sessionId);
            if (status === 200)
                return data;
        }
        catch (err) {
            if (err instanceof ApiError && err.status === 404 && !restarted) { // the backend restarted while the report was being made
                restarted = true;
                await finishLesson(sessionId);
            }
            else if (!(err instanceof ApiError) || err.status !== 0)
                throw err;
        }
        await new Promise(r => setTimeout(r, everyMs));
    }
    throw new ApiError(0, 'Laporan belum selesai. Coba lagi sebentar.');
}
