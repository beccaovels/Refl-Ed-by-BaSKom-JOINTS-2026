import './styles.css';
import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter as BrowserRouter, Link, NavLink, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { CalendarDays, ChartNoAxesCombined, ChevronDown, ChevronLeft, ChevronRight, CircleCheck, Clock3, FileText, History, Home, Menu, Mic, MicOff, Camera, CameraOff, Pause, Play, Plus, Radio, RefreshCw, Settings2, ShieldCheck, Sparkles, Square, X, ArrowRight, Upload, WifiOff, AlertCircle } from 'lucide-react';
import { formatDate, formatTime, image, lessons, switchDemoProfile, lessonFromParams, reportTrends, readStore, saveStore } from './data.js';
import * as api from './api.js';
import { startRecorder } from './audio.js';
import { adaptReport } from './adapt.js';

const Context = createContext(null);
const useApp = () => useContext(Context);
function App() {
    const [user, setUser] = useState(api.getUser);
    const [store, setStore] = useState(readStore);
    const [storageError, setStorageError] = useState(false);
    useEffect(() => {
        try {
            saveStore(store);
            setStorageError(false);
        }
        catch {
            setStorageError(true);
        }
    }, [store]);
    if (!user)
        return _jsx(Login, { onLogin: setUser });
    return _jsx(Context.Provider, { value: { store, setStore, user, logout: () => { api.logout(); setUser(null); } }, children: _jsxs(BrowserRouter, { children: [storageError && _jsxs("div", { className: "storage-error", role: "alert", children: ["Penyimpanan peramban penuh atau tidak tersedia. Perubahan belum tersimpan. ", _jsx("button", { onClick: () => {
                                try {
                                    saveStore(store);
                                    setStorageError(false);
                                }
                                catch {
                                    setStorageError(true);
                                }
                            }, children: "Coba simpan lagi" })] }), _jsx(Shell, {})] }) });
}
const nav = [{ to: '/', label: 'Dashboard', icon: Home }, { to: '/schedule', label: 'Jadwal', icon: CalendarDays }, { to: '/history', label: 'Riwayat', icon: History }, { to: '/performance', label: 'Performa', icon: ChartNoAxesCombined }];
function Shell() {
    const { user, logout } = useApp();
    const location = useLocation();
    const [open, setOpen] = useState(false);
    const [collapsed, setCollapsed] = useState(false);
    useDialogFocus(open, () => setOpen(false));
    useEffect(() => {
        window.scrollTo(0, 0);
        setOpen(false);
        if (!['/simulator/check', '/simulator/room'].includes(location.pathname)) {
            deviceStream?.getTracks().forEach(t => t.stop());
            deviceStream = null;
        }
    }, [location.pathname]);
    useEffect(() => {
        if (!open)
            return;
        const close = (e) => {
            if (e.key === 'Escape')
                setOpen(false);
        };
        window.addEventListener('keydown', close);
        return () => window.removeEventListener('keydown', close);
    }, [open]);
    return _jsxs(_Fragment, { children: [_jsx("a", { className: "skip-link", href: "#main-content", children: "Lewati ke konten" }), _jsxs("div", { className: `app-shell ${collapsed ? 'nav-collapsed' : ''}`, children: [_jsx("button", { className: "mobile-menu icon-button", onClick: () => setOpen(true), "aria-label": "Buka navigasi", children: _jsx(Menu, { size: 22 }) }), open && _jsx("button", { className: "nav-scrim", "aria-label": "Tutup navigasi", onClick: () => setOpen(false) }), _jsxs("aside", { role: open ? 'dialog' : undefined, "aria-modal": open ? true : undefined, "aria-label": "Menu GeMa", className: `sidebar ${open ? 'open' : ''}`, children: [_jsxs("div", { className: "brand", children: [_jsxs("span", { className: "brand-mark", children: ["g", _jsx("span", { children: "." })] }), _jsxs("span", { className: "brand-copy", children: [_jsx("strong", { children: "GeMa" }), _jsx("small", { children: "Ruang berlatih guru" })] }), _jsx("button", { className: "close-nav icon-button", "aria-label": "Tutup navigasi", onClick: () => setOpen(false), children: _jsx(X, { size: 20 }) })] }), _jsx("div", { className: "nav-caption", children: "RUANG KERJA" }), _jsx("nav", { "aria-label": "Navigasi utama", children: nav.map(({ to, label, icon: Icon }) => _jsxs(NavLink, { to: to, end: to === '/', onClick: () => setOpen(false), className: ({ isActive }) => `nav-link ${isActive || (to === '/performance' && location.pathname.startsWith('/report/')) ? 'active' : ''}`, title: label, "aria-label": label, children: [_jsx(Icon, { size: 20 }), _jsx("span", { children: label })] }, to)) }), _jsxs("div", { className: "sidebar-bottom", children: [_jsxs("div", { className: "sidebar-message", children: [_jsx(Sparkles, { size: 18 }), _jsxs("span", { children: ["AI adalah cermin,", _jsx("br", {}), "bukan penilai."] })] }), _jsxs("button", { className: "collapse-button", onClick: () => setCollapsed(!collapsed), "aria-label": collapsed ? 'Perluas navigasi' : 'Ciutkan navigasi', children: [_jsx(ChevronLeft, { size: 18, className: collapsed ? 'rotated' : '' }), _jsx("span", { children: "Ciutkan menu" })] })] })] }), _jsxs("main", { className: "main", id: "main-content", tabIndex: -1, children: [_jsxs("div", { className: "topbar", children: [_jsxs("span", { className: "topbar-label", children: ["GeMa ", _jsx("span", { children: "/" }), " Ruang latihan"] }), _jsxs("div", { className: "topbar-right", children: [_jsxs("span", { className: "demo-pill", children: [_jsx("span", { className: "dot" }), " MODE DEMO"] }), _jsx("button", { className: "text-link logout-link", onClick: logout, children: `Keluar (${user.name})` }), _jsx("span", { className: "avatar", "aria-label": `Masuk sebagai ${user.name}`, title: user.name, children: user.name.trim()[0]?.toUpperCase() ?? "G" })] })] }), _jsx(Reminder, {}), _jsxs(Routes, { children: [_jsx(Route, { path: "/", element: _jsx(Dashboard, {}) }), _jsx(Route, { path: "/schedule", element: _jsx(Schedule, {}) }), _jsx(Route, { path: "/history", element: _jsx(HistoryPage, {}) }), _jsx(Route, { path: "/performance", element: _jsx(PerformanceOverview, {}) }), _jsx(Route, { path: "/report/:id", element: _jsx(ReportPage, {}) }), _jsx(Route, { path: "/simulator/setup", element: _jsx(Setup, {}) }), _jsx(Route, { path: "/simulator/check", element: _jsx(DeviceCheck, {}) }), _jsx(Route, { path: "/simulator/room", element: _jsx(Room, {}) }), _jsx(Route, { path: "*", element: _jsx(Dashboard, {}) })] })] })] })] });
}
function Login({ onLogin }) {
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);
    async function submit(e) {
        e.preventDefault();
        if (!name.trim() || busy)
            return;
        setBusy(true);
        setError('');
        try {
            onLogin(await api.login(name));
        }
        catch (err) {
            setError(err.message);
            setBusy(false);
        }
    }
    return _jsx("main", { className: "login-page", children: _jsxs("form", { className: "card login-card", onSubmit: submit, children: [
        _jsx("span", { className: "section-kicker green", children: "MODE DEMO" }),
        _jsx("h1", { children: "Masuk sebagai guru" }),
        _jsx("p", { className: "muted", children: "Tanpa kata sandi. Cukup tulis nama; latihan dan laporan Anda disimpan di laptop ini." }),
        _jsxs("label", { children: ["Nama Anda", _jsx("input", { value: name, onChange: e => setName(e.target.value), autoFocus: true, maxLength: 100, placeholder: "Contoh: Bu Rina", required: true })] }),
        error && _jsx("span", { className: "error-text", role: "alert", children: error }),
        _jsx("button", { className: "button button-primary", type: "submit", disabled: !name.trim() || busy, children: busy ? "Masuk..." : "Masuk" })
    ] }) });
}
function PageHeading({ eyebrow, title, description, action }) { return _jsxs("div", { className: "page-heading", children: [_jsxs("div", { children: [_jsx("p", { className: "eyebrow", children: eyebrow }), _jsx("h1", { children: title }), _jsx("p", { className: "page-subtitle", children: description })] }), action] }); }
function Button({ children, to, onClick, variant = 'primary', icon: Icon, type = 'button', disabled = false }) { const cls = `button button-${variant}`; return to ? _jsxs(Link, { className: cls, to: to, children: [Icon && _jsx(Icon, { size: 18 }), _jsx("span", { children: children })] }) : _jsxs("button", { className: cls, onClick: onClick, type: type, disabled: disabled, children: [Icon && _jsx(Icon, { size: 18 }), _jsx("span", { children: children })] }); }
function Empty({ title, body, art, action }) { return _jsxs("div", { className: "empty-state", children: [_jsx("img", { src: image(art), alt: "" }), _jsxs("div", { children: [_jsx("h3", { children: title }), _jsx("p", { children: body }), action] })] }); }
function useSchedules() { const { store } = useApp(); const [now, setNow] = useState(Date.now()); useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 15000); return () => clearInterval(timer); }, []); return store.schedules.map(s => ({ ...s, missed: s.status === 'scheduled' && new Date(s.at).getTime() < now })).sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime()); }
function lessonUrl(item, scheduleId) {
    const p = new URLSearchParams({ kelas: item.kelas, subject: item.subject, chapter: item.chapter, subchapter: item.subchapter });
    if (scheduleId)
        p.set('scheduleId', scheduleId);
    return `/simulator/setup?${p}`;
}
function Dashboard() { const { store, setStore } = useApp(); const upcoming = useSchedules().filter(s => !s.missed && s.status === 'scheduled').slice(0, 3); const latest = [...store.reports].sort((a, b) => b.completedAt.localeCompare(a.completedAt))[0]; return _jsxs("div", { className: "page", children: [_jsx(ResumeDraft, {}), _jsx(PageHeading, { eyebrow: "SELAMAT DATANG KEMBALI", title: store.reports.length ? "Selamat datang kembali!" : "Selamat datang di GeMa!", description: "Siap memberi ruang untuk satu latihan kecil hari ini?" }), _jsxs("section", { className: "hero", children: [_jsxs("div", { className: "hero-content", children: [_jsxs("span", { className: "hero-tag", children: [_jsx(Sparkles, { size: 15 }), " RUANG AMAN UNTUK MENCOBA"] }), _jsxs("h2", { children: ["Latihan hari ini,", _jsx("br", {}), _jsx("em", { children: "lebih percaya diri" }), " esok hari."] }), _jsx("p", { children: "Jelaskan materi, hadapi pertanyaan Siswa GeMa, lalu lihat refleksi yang bisa langsung dicoba." }), _jsx(Button, { to: "/simulator/setup", icon: Play, children: "Mulai Sesi" }), _jsx("span", { className: "hero-note", children: "Langsung ke persiapan \u2022 sekitar 2 menit" })] }), _jsx("img", { src: image('teachers/teacher-explaining-teenagers.png'), alt: "Guru menjelaskan materi kepada dua siswa remaja" })] }), _jsxs("div", { className: "dashboard-grid", children: [_jsxs("section", { className: "card section-card", children: [_jsxs("div", { className: "section-heading", children: [_jsxs("div", { children: [_jsx("span", { className: "section-kicker green", children: "LANGKAH BERIKUTNYA" }), _jsx("h2", { children: "Jadwal terdekat" })] }), _jsxs(Link, { to: "/schedule", className: "text-link", children: ["Lihat jadwal ", _jsx(ArrowRight, { size: 16 })] })] }), upcoming.length ? _jsx("div", { className: "session-stack", children: upcoming.map(s => _jsxs(Link, { to: lessonUrl(s, s.id), className: "schedule-row", children: [_jsxs("span", { className: "date-tile", children: [_jsx("strong", { children: new Date(s.at).getDate() }), _jsx("small", { children: formatDate(s.at, { month: 'short' }).toUpperCase() })] }), _jsxs("span", { className: "row-main", children: [_jsxs("strong", { children: [s.subject, " \u00B7 ", s.chapter] }), _jsxs("small", { children: [s.subchapter, " \u2022 ", s.kelas] }), _jsxs("small", { children: [_jsx(Clock3, { size: 13 }), " ", formatDate(s.at, { weekday: 'long' }), ", ", formatTime(s.at), " (waktu lokal)"] })] }), _jsx(ChevronRight, { size: 19 })] }, s.id)) }) : _jsx(Empty, { title: "Belum ada latihan terjadwal", body: "Pilih waktu yang cocok, lalu GeMa akan mengingatkan saat aplikasi terbuka.", art: "schedule/upcoming-teaching-session.png", action: _jsx(Button, { to: "/schedule", variant: "secondary", icon: Plus, children: "Buat jadwal" }) })] }), _jsxs("section", { className: "card section-card snapshot-card", children: [_jsxs("div", { className: "section-heading", children: [_jsxs("div", { children: [_jsx("span", { className: "section-kicker coral", children: "REFLEKSI TERAKHIR" }), _jsx("h2", { children: "Jejak latihan" })] }), _jsxs(Link, { to: "/history", className: "text-link", children: ["Riwayat ", _jsx(ArrowRight, { size: 16 })] })] }), latest ? _jsxs(_Fragment, { children: [_jsxs("div", { className: "snapshot", children: [_jsxs("div", { className: "score-bubble", children: [latest.overall?.toFixed(1) ?? '—', _jsx("small", { children: "/ 5" })] }), _jsxs("div", { children: [_jsx("span", { className: "muted small", children: formatDate(latest.completedAt) }), _jsxs("h3", { children: [latest.lesson.subject, " \u00B7 ", latest.lesson.chapter] }), _jsx("p", { children: latest.demo ? 'Contoh laporan dalam mode demo.' : 'Laporan latihan Anda tersimpan.' })] })] }), _jsx(Button, { to: `/report/${latest.id}`, variant: "secondary", icon: FileText, children: "Buka laporan" })] }) : _jsx(Empty, { title: "Setiap latihan punya ceritanya", body: "Mulai sesi pertama untuk melihat refleksi pribadi Anda di sini.", art: "brand-elements/reflection-growth.png", action: _jsx(Button, { to: "/simulator/setup", variant: "secondary", children: "Mulai latihan" }) })] })] }), _jsx(TopicCards, {}), _jsxs("div", { className: "demo-switch", children: [_jsxs("span", { children: [_jsx("strong", { children: "Pratinjau data" }), _jsx("small", { children: "Dua profil demo terpisah. Jadwal dan latihan Anda tetap tersimpan saat berpindah profil." })] }), _jsx("button", { onClick: () => setStore(switchDemoProfile(store)), className: "switch-button", children: store.mode === 'seeded' ? 'Lihat keadaan guru baru' : 'Muat contoh guru kembali' })] })] }); }
function LessonFields({ value, onChange }) { const subjects = [...new Set(lessons.map(l => l.subject))]; const chapters = lessons.filter(l => l.subject === value.subject); return _jsxs("div", { className: "field-grid", children: [_jsxs("label", { children: ["Kelas", _jsx("select", { value: value.kelas, onChange: e => onChange({ ...value, kelas: e.target.value }), children: ['Kelas VII', 'Kelas VIII'].map(x => _jsx("option", { children: x }, x)) })] }), _jsxs("label", { children: ["Mata pelajaran", _jsx("select", { value: value.subject, onChange: e => { const next = lessons.find(l => l.subject === e.target.value); onChange({ ...next, kelas: value.kelas }); }, children: subjects.map(x => _jsx("option", { children: x }, x)) })] }), _jsxs("label", { children: ["Bab", _jsx("select", { value: value.chapter, onChange: e => { const next = chapters.find(l => l.chapter === e.target.value); onChange({ ...next, kelas: value.kelas }); }, children: chapters.map(x => _jsx("option", { children: x.chapter }, x)) })] }), _jsxs("label", { children: ["Sub-bab", _jsx("select", { value: value.subchapter, onChange: e => onChange({ ...value, subchapter: e.target.value }), children: chapters.filter(l => l.chapter === value.chapter).map(x => _jsx("option", { children: x.subchapter }, x.subchapter)) })] })] }); }
function Schedule() {
    const { store, setStore } = useApp();
    const navigate = useNavigate();
    const [params, setParams] = useSearchParams();
    const schedules = useSchedules();
    const [month, setMonth] = useState(() => new Date());
    const [selected, setSelected] = useState(() => new Date());
    const [editing, setEditing] = useState(null);
    const [showForm, setShowForm] = useState(params.has('subject'));
    const [lesson, setLesson] = useState(() => lessonFromParams(params));
    const [date, setDate] = useState(() => { const d = new Date(Date.now() + 86400000); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; });
    const [time, setTime] = useState('10:00');
    const [error, setError] = useState('');
    const first = new Date(month.getFullYear(), month.getMonth(), 1);
    const offset = (first.getDay() + 6) % 7;
    const days = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
    const dateKey = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    function openForm(item) { setEditing(item ?? null); setLesson(item ? { kelas: item.kelas, subject: item.subject, chapter: item.chapter, subchapter: item.subchapter } : lessons[0]); setDate(item ? dateKey(new Date(item.at)) : dateKey(selected)); setTime(item ? `${String(new Date(item.at).getHours()).padStart(2, '0')}:${String(new Date(item.at).getMinutes()).padStart(2, '0')}` : '10:00'); setError(''); setShowForm(true); }
    function save(e) {
        e.preventDefault();
        const at = new Date(`${date}T${time}`);
        if (!date || Number.isNaN(at.getTime())) {
            setError('Pilih tanggal dan jam yang valid.');
            return;
        }
        if (at.getTime() <= Date.now()) {
            setError('Waktu latihan harus di masa depan. Pilih tanggal atau jam lain.');
            return;
        }
        const item = { id: editing?.id ?? crypto.randomUUID(), ...lesson, at: at.toISOString(), status: 'scheduled' };
        setStore(prev => ({ ...prev, schedules: editing ? prev.schedules.map(s => s.id === editing.id ? item : s) : [...prev.schedules, item] }));
        setShowForm(false);
        setParams({});
        setSelected(at);
        setMonth(at);
    }
    const candidate = date && time ? new Date(`${date}T${time}`).getTime() : 0;
    const overlap = store.schedules.some(s => s.id !== editing?.id && s.status === 'scheduled' && Math.abs(new Date(s.at).getTime() - candidate) < 60 * 60 * 1000);
    const upcoming = schedules.filter(s => !s.missed && s.status === 'scheduled');
    const missed = schedules.filter(s => s.missed);
    const monthLabel = formatDate(first, { month: 'long', year: 'numeric' });
    useDialogFocus(showForm, () => setShowForm(false));
    return _jsxs("div", { className: "page", children: [_jsx(PageHeading, { eyebrow: "ATUR RITME LATIHAN", title: "Jadwal latihan", description: "Sisihkan waktu yang pas. Setiap jadwal membawa topik langsung ke ruang latihan.", action: _jsx(Button, { onClick: () => openForm(), icon: Plus, children: "Jadwalkan latihan" }) }), _jsxs("div", { className: "schedule-layout", children: [_jsxs("section", { className: "card calendar-card", children: [_jsxs("div", { className: "calendar-top", children: [_jsxs("div", { children: [_jsx("span", { className: "section-kicker green", children: "KALENDER" }), _jsx("h2", { children: monthLabel })] }), _jsxs("div", { className: "month-actions", children: [_jsx("button", { className: "icon-button", "aria-label": "Bulan sebelumnya", onClick: () => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1)), children: _jsx(ChevronLeft, {}) }), _jsx("button", { className: "icon-button", "aria-label": "Bulan berikutnya", onClick: () => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1)), children: _jsx(ChevronRight, {}) })] })] }), _jsx("div", { className: "calendar-grid weekdays", children: ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'].map(x => _jsx("span", { children: x }, x)) }), _jsxs("div", { className: "calendar-grid days", children: [Array.from({ length: offset }, (_, i) => _jsx("span", {}, `blank-${i}`)), Array.from({ length: days }, (_, i) => { const d = new Date(month.getFullYear(), month.getMonth(), i + 1), k = dateKey(d), count = schedules.filter(s => dateKey(new Date(s.at)) === k).length; return _jsxs("button", { className: `day ${dateKey(selected) === k ? 'selected' : ''} ${dateKey(new Date()) === k ? 'today' : ''}`, onClick: () => setSelected(d), "aria-pressed": dateKey(selected) === k, "aria-label": `${formatDate(d.toISOString())}, ${count} sesi`, children: [_jsx("span", { children: i + 1 }), count > 0 && _jsx("span", { className: "calendar-dot" })] }, k); })] }), _jsxs("div", { className: "selected-day", children: [_jsx("h3", { children: formatDate(selected.toISOString(), { weekday: 'long', day: 'numeric', month: 'long' }) }), schedules.filter(s => dateKey(new Date(s.at)) === dateKey(selected)).map(s => _jsxs(Link, { to: lessonUrl(s, s.id), children: [formatTime(s.at), " \u00B7 ", s.subject, " \u2014 ", s.chapter, _jsx("span", { className: "status", children: s.status === 'done' ? 'Selesai' : s.missed ? 'Terlewat' : 'Terjadwal' })] }, s.id)), !schedules.some(s => dateKey(new Date(s.at)) === dateKey(selected)) && _jsx("p", { className: "muted small", children: "Belum ada latihan pada tanggal ini." })] }), _jsxs("div", { className: "calendar-footer", children: [_jsxs("span", { children: [_jsx("span", { className: "calendar-dot" }), " Ada latihan"] }), _jsxs(Button, { onClick: () => openForm(), variant: "subtle", icon: Plus, children: ["Tambah di ", formatDate(selected.toISOString(), { day: 'numeric', month: 'long' })] })] })] }), _jsxs("section", { className: "card upcoming-card", children: [_jsxs("div", { className: "section-heading", children: [_jsxs("div", { children: [_jsx("span", { className: "section-kicker coral", children: "SELANJUTNYA" }), _jsx("h2", { children: "Latihan mendatang" })] }), _jsxs("span", { className: "count-pill", children: [upcoming.length, " sesi"] })] }), _jsx("p", { className: "muted small", children: "Pengingat tampil di aplikasi saat GeMa terbuka. Notifikasi luar aplikasi belum tersedia dalam demo." }), upcoming.length ? _jsx("div", { className: "upcoming-list", children: upcoming.map(s => _jsxs("div", { className: "upcoming-item", children: [_jsx("div", { className: "upcoming-icon", children: _jsx(CalendarDays, { size: 20 }) }), _jsxs("div", { className: "upcoming-copy", children: [_jsxs("strong", { children: [s.subject, " \u00B7 ", s.chapter] }), _jsxs("small", { children: [s.subchapter, " \u00B7 ", s.kelas] }), _jsxs("small", { children: [formatDate(s.at, { weekday: 'long', day: 'numeric', month: 'short' }), " \u00B7 ", formatTime(s.at), " (waktu lokal)"] }), _jsxs("div", { className: "inline-actions", children: [_jsxs("button", { onClick: () => navigate(lessonUrl(s, s.id)), children: ["Mulai sesi ", _jsx(ArrowRight, { size: 14 })] }), _jsx("button", { onClick: () => openForm(s), children: "Ubah" })] })] })] }, s.id)) }) : _jsx(Empty, { title: "Belum ada sesi", body: "Buat jadwal pertama agar waktu latihan terasa lebih mudah dijaga.", art: "schedule/upcoming-teaching-session.png", action: _jsx(Button, { onClick: () => openForm(), variant: "secondary", icon: Plus, children: "Buat jadwal" }) })] })] }), missed.length > 0 && _jsxs("section", { className: "card missed-card", children: [_jsx("h2", { children: "Sesi terlewat" }), _jsx("p", { className: "muted", children: "Waktu telah lewat, tetapi rencana latihan Anda tetap tersimpan." }), missed.map(s => _jsxs("div", { className: "missed-row", children: [_jsxs("span", { children: [_jsxs("strong", { children: [s.subject, " \u00B7 ", s.chapter] }), _jsxs("small", { children: [formatDate(s.at), " \u00B7 ", formatTime(s.at), " (waktu lokal)"] })] }), _jsx("span", { className: "status status-warn", children: "Terlewat" }), _jsx(Button, { onClick: () => openForm(s), variant: "subtle", children: "Jadwalkan ulang" })] }, s.id))] }), showForm && _jsx("div", { className: "modal-backdrop", onMouseDown: e => {
                    if (e.target === e.currentTarget)
                        setShowForm(false);
                }, children: _jsxs("div", { className: "modal", role: "dialog", "aria-modal": "true", "aria-labelledby": "schedule-title", children: [_jsxs("div", { className: "modal-head", children: [_jsxs("div", { children: [_jsx("span", { className: "section-kicker green", children: "WAKTU UNTUK BERTUMBUH" }), _jsx("h2", { id: "schedule-title", children: editing ? 'Ubah jadwal' : 'Jadwalkan latihan' })] }), _jsx("button", { className: "icon-button", "aria-label": "Tutup formulir", onClick: () => setShowForm(false), children: _jsx(X, {}) })] }), _jsxs("form", { onSubmit: save, children: [_jsx(LessonFields, { value: lesson, onChange: setLesson }), _jsxs("div", { className: "field-grid", children: [_jsxs("label", { children: ["Tanggal", _jsx("input", { type: "date", value: date, onChange: e => setDate(e.target.value), required: true })] }), _jsxs("label", { children: ["Jam (waktu lokal)", _jsx("input", { type: "time", value: time, onChange: e => setTime(e.target.value), required: true })] })] }), overlap && _jsxs("div", { className: "notice warning", children: [_jsx(AlertCircle, { size: 18 }), _jsx("span", { children: "Ada jadwal lain dalam rentang satu jam. Anda tetap dapat menyimpan keduanya." })] }), error && _jsxs("div", { className: "notice error", role: "alert", children: [_jsx(AlertCircle, { size: 18 }), error] }), _jsxs("div", { className: "modal-actions", children: [_jsx(Button, { onClick: () => setShowForm(false), variant: "subtle", children: "Batal" }), _jsx(Button, { type: "submit", icon: CircleCheck, children: "Simpan jadwal" })] })] })] }) })] });
}
function HistoryPage() { const { store } = useApp(); const [subject, setSubject] = useState('Semua mapel'); const [chapter, setChapter] = useState('Semua bab'); const subjects = [...new Set(store.reports.map(r => r.lesson.subject))]; const chapters = [...new Set(store.reports.filter(r => subject === 'Semua mapel' || r.lesson.subject === subject).map(r => r.lesson.chapter))]; const reports = [...store.reports].filter(r => (subject === 'Semua mapel' || r.lesson.subject === subject) && (chapter === 'Semua bab' || r.lesson.chapter === chapter)).sort((a, b) => b.completedAt.localeCompare(a.completedAt)); return _jsxs("div", { className: "page", children: [_jsx(PageHeading, { eyebrow: "ARSIP REFLEKSI", title: "Riwayat latihan", description: "Temukan kembali momen belajar Anda. Setiap laporan tersimpan persis seperti saat sesi selesai.", action: _jsx(Button, { to: "/simulator/setup", icon: Play, children: "Mulai Sesi" }) }), _jsxs("div", { className: "history-intro", children: [_jsxs("div", { children: [_jsx("span", { className: "section-kicker coral", children: "PERJALANAN ANDA" }), _jsx("h2", { children: "Satu latihan, satu langkah maju." }), _jsx("p", { children: "Gunakan laporan untuk memilih hal kecil yang ingin dicoba pada sesi berikutnya." })] }), _jsx("img", { src: image('brand-elements/reflection-growth.png'), alt: "Guru dan siswa berbagi semangat belajar" })] }), _jsxs("section", { className: "card history-card", children: [_jsxs("div", { className: "section-heading history-heading", children: [_jsxs("div", { children: [_jsx("span", { className: "section-kicker green", children: "SEMUA SESI" }), _jsxs("h2", { children: ["Laporan tersimpan ", _jsx("span", { className: "count-pill", children: store.reports.length })] })] }), _jsxs("div", { className: "filters", children: [_jsx("label", { className: "sr-only", htmlFor: "subject-filter", children: "Filter mata pelajaran" }), _jsxs("select", { id: "subject-filter", value: subject, onChange: e => { setSubject(e.target.value); setChapter('Semua bab'); }, children: [_jsx("option", { children: "Semua mapel" }), subjects.map(x => _jsx("option", { children: x }, x))] }), _jsx("label", { className: "sr-only", htmlFor: "chapter-filter", children: "Filter bab" }), _jsxs("select", { id: "chapter-filter", value: chapter, onChange: e => setChapter(e.target.value), children: [_jsx("option", { children: "Semua bab" }), chapters.map(x => _jsx("option", { children: x }, x))] })] })] }), reports.length ? _jsx("div", { className: "report-list", children: reports.map(r => _jsxs(Link, { to: `/report/${r.id}`, className: "report-row", children: [_jsx("span", { className: "report-subject-icon", children: r.lesson.subject === 'Matematika' ? _jsx(Settings2, { size: 24 }) : _jsx(Sparkles, { size: 24 }) }), _jsxs("span", { className: "report-row-copy", children: [_jsxs("strong", { children: [r.lesson.subject, " \u00B7 ", r.lesson.chapter] }), _jsxs("small", { children: [r.lesson.subchapter, " \u00B7 ", r.lesson.kelas] }), _jsxs("small", { children: [_jsx(CalendarDays, { size: 13 }), formatDate(r.completedAt), " \u00B7 ", r.duration, " menit"] })] }), _jsxs("span", { className: "report-row-end", children: [_jsx("span", { className: `status ${r.status === 'complete' ? 'status-green' : 'status-warn'}`, children: r.status === 'complete' ? 'Selesai' : r.status === 'limited' ? 'Terbatas' : 'Umpan balik belum tersedia' }), _jsx("strong", { children: r.overall === null ? '—' : `${r.overall.toFixed(1)} / 5` })] }), _jsx(ChevronRight, { size: 19 })] }, r.id)) }) : _jsx(Empty, { title: store.reports.length ? 'Tidak ada sesi yang cocok' : 'Belum ada riwayat latihan', body: store.reports.length ? 'Coba pilih mata pelajaran atau bab lain.' : 'Saat sesi pertama selesai, laporan refleksinya akan tampil di sini.', art: "ui-states/loading-lesson-preparation.png", action: store.reports.length ? _jsx(Button, { onClick: () => { setSubject('Semua mapel'); setChapter('Semua bab'); }, variant: "secondary", children: "Hapus filter" }) : _jsx(Button, { to: "/simulator/setup", icon: Play, children: "Mulai Sesi" }) })] })] }); }
function PerformanceOverview() { const { store } = useApp(); const reports = [...store.reports].sort((a, b) => b.completedAt.localeCompare(a.completedAt)); const valid = reports; const trends = reportTrends(reports); return _jsxs("div", { className: "page", children: [_jsx(PageHeading, { eyebrow: "CERMIN LATIHAN", title: "Performa", description: "Refleksi pribadi yang membantu Anda memilih latihan berikutnya, tanpa peringkat atau perbandingan dengan guru lain.", action: _jsx(Button, { to: "/simulator/setup", icon: Play, children: "Mulai Sesi" }) }), _jsxs("div", { className: "performance-hero card", children: [_jsxs("div", { children: [_jsx("span", { className: "section-kicker green", children: "AI ADALAH CERMIN, BUKAN PENILAI" }), _jsx("h2", { children: "Lihat apa yang sudah kuat. Pilih satu hal untuk dilatih lagi." }), _jsx("p", { children: "Skor latihan adalah penunjuk untuk refleksi pribadi. Bukti dari percakapan membantu menjelaskan setiap catatan." })] }), _jsx("img", { src: image('students/teenagers-science-project.png'), alt: "Siswa bekerja sama dalam proyek sains" })] }), valid.length ? _jsxs("div", { className: "performance-grid", children: [_jsxs("section", { className: "card section-card", children: [_jsx("span", { className: "section-kicker coral", children: "LAPORAN TERAKHIR" }), _jsxs("h2", { children: [valid[0].lesson.subject, " \u00B7 ", valid[0].lesson.chapter] }), _jsxs("div", { className: "performance-score", children: [_jsx("strong", { children: valid[0].overall?.toFixed(1) ?? '—' }), _jsxs("span", { children: ["/ 5", _jsx("br", {}), _jsx("small", { children: valid[0].demo ? 'skor latihan contoh' : 'skor belum tersedia' })] })] }), _jsxs("p", { className: "muted", children: [formatDate(valid[0].completedAt), " \u00B7 ", valid[0].duration, " menit"] }), _jsx(Button, { to: `/report/${valid[0].id}`, variant: "secondary", icon: FileText, children: "Lihat laporan lengkap" })] }), _jsxs("section", { className: "card section-card", children: [_jsx("span", { className: "section-kicker green", children: "POLA LATIHAN" }), _jsx("h2", { children: "Perkembangan topik" }), trends.length ? _jsx("div", { className: "trend-list", children: trends.map(t => _jsxs("div", { children: [_jsx("strong", { children: t.topic }), _jsxs("p", { children: [t.demo ? 'Data contoh · ' : '', t.delta > 0 ? 'Naik' : t.delta < 0 ? 'Turun' : 'Tetap', " ", Math.abs(t.delta).toFixed(1), " poin dari sesi sebelumnya"] }), _jsxs("small", { children: [t.values.join(' → '), " / 5 \u00B7 tiga sesi terakhir"] })] }, t.topic)) }) : _jsxs(_Fragment, { children: [_jsx("p", { className: "muted", children: "Tren muncul setelah ada sedikitnya tiga sesi pada bab yang sama. Saat ini belum cukup data untuk menyimpulkan perubahan." }), _jsxs("div", { className: "trend-placeholder", children: [_jsx(ChartNoAxesCombined, { size: 30 }), _jsx("span", { children: "Terus berlatih pada topik yang sama untuk melihat pola." })] })] })] })] }) : _jsx(Empty, { title: "Belum ada refleksi", body: "Selesaikan satu latihan untuk mulai membangun arsip laporan Anda.", art: "brand-elements/reflection-growth.png", action: _jsx(Button, { to: "/simulator/setup", children: "Mulai Sesi" }) })] }); }
function ReportPage() {
    const { id } = useParams();
    const { store } = useApp();
    const r = store.reports.find(x => x.id === id);
    const [active, setActive] = useState(null);
    if (!r)
        return _jsx("div", { className: "page", children: _jsx(PageHeading, { eyebrow: "LAPORAN", title: "Laporan tidak ditemukan", description: "Sesi ini tidak ada di penyimpanan lokal peramban.", action: _jsx(Button, { to: "/history", variant: "secondary", children: "Kembali ke riwayat" }) }) });
    return _jsxs("div", { className: "page report-page", children: [_jsxs("div", { className: "report-back", children: [_jsxs(Link, { to: "/history", children: [_jsx(ChevronLeft, { size: 17 }), " Riwayat latihan"] }), _jsx("span", { className: "demo-pill", children: r.demo ? 'CONTOH DEMO' : 'SESI LOKAL' })] }), _jsx(PageHeading, { eyebrow: "LAPORAN REFLEKSI", title: `${r.lesson.subject} · ${r.lesson.chapter}`, description: `${r.lesson.subchapter} · ${r.lesson.kelas} · ${formatDate(r.completedAt)} · ${r.duration} menit` }), _jsxs("div", { className: "report-top", children: [_jsxs("div", { className: "card score-panel", children: [_jsxs("div", { className: "score-ring", children: [_jsx("strong", { children: r.overall?.toFixed(1) ?? '—' }), _jsx("span", { children: "/ 5" })] }), _jsxs("div", { children: [_jsx("span", { className: "section-kicker coral", children: "SKOR LATIHAN" }), _jsx("h2", { children: r.status === 'complete' ? 'Ruang untuk bertumbuh' : 'Umpan balik terbatas' }), _jsx("p", { children: r.demo ? 'Angka dan bukti di laporan ini adalah data contoh untuk memperagakan alur, bukan analisis AI terhadap sesi Anda.' : 'Laporan ini disusun dari transkrip sesi Anda. Anda bebas tidak setuju dengan bagian mana pun.' }), _jsx("span", { className: "quote-line", children: "AI adalah cermin, bukan penilai." })] })] }), _jsxs("div", { className: "card report-next", children: [_jsx("span", { className: "section-kicker green", children: "LANJUTKAN LATIHAN" }), _jsx("h2", { children: "Langkah berikutnya sudah dekat." }), _jsx("p", { children: "Coba kembali topik yang sama atau sisihkan waktu untuk sesi berikutnya." }), _jsx(Button, { to: lessonUrl(r.lesson), icon: RefreshCw, children: "Latih lagi" }), _jsx(Button, { to: lessonUrl(r.lesson).replace('/simulator/setup', '/schedule'), variant: "secondary", icon: CalendarDays, children: "Jadwalkan latihan" })] })] }), r.status !== 'complete' && _jsxs("div", { className: "notice warning", children: [_jsx(AlertCircle, { size: 18 }), _jsx("span", { children: r.status === 'limited' ? 'Sesi singkat: bukti belum cukup untuk penilaian penuh.' : 'Umpan balik otomatis belum tersedia dalam mode ini. Anda tetap dapat membaca catatan sesi.' })] }), r.material && _jsxs("div", { className: "notice neutral", children: [_jsx(FileText, { size: 18 }), " Nama materi: ", r.material, " \u00B7 isi PDF tidak disimpan atau dianalisis."] }), _jsxs("div", { className: "report-columns", children: [_jsxs("section", { className: "card report-section", children: [_jsx("div", { className: "section-heading", children: _jsxs("div", { children: [_jsx("span", { className: "section-kicker green", children: "RUBRIK 1\u20135" }), _jsx("h2", { children: "Yang terlihat dari latihan" })] }) }), _jsx("p", { className: "rubric-key", children: "1 \u00B7 Perlu latihan \u00A0 2 \u00B7 Mulai terbentuk \u00A0 3 \u00B7 Cukup jelas \u00A0 4 \u00B7 Kuat \u00A0 5 \u00B7 Konsisten" }), _jsx("div", { className: "dimension-list", children: r.dimensions.map((d, i) => _jsxs("div", { className: "dimension", children: [_jsxs("div", { className: "dimension-title", children: [_jsx("strong", { children: d.name }), _jsx("span", { children: d.score === null ? 'Tidak tersedia' : `${d.score} / 5` })] }), _jsx("div", { className: "rating-bars", "aria-label": d.score === null ? `${d.name}: tidak tersedia` : `${d.name}: ${d.score} dari 5`, children: Array.from({ length: 5 }, (_, j) => _jsx("span", { className: d.score !== null && j < d.score ? 'filled' : '' }, j)) }), _jsx("p", { children: d.summary }), d.evidence !== undefined && _jsxs("button", { className: "evidence-link", onClick: () => { setActive(d.evidence); document.getElementById(`moment-${d.evidence}`)?.focus(); }, children: [_jsx(Clock3, { size: 14 }), " Lihat bukti ", r.moments[d.evidence]?.at] }), i === 2 && _jsx("div", { className: "dimension-separator" })] }, d.name)) }), !r.camera && _jsxs("div", { className: "notice neutral", children: [_jsx(CameraOff, { size: 18 }), " Kehadiran di kamera tidak dinilai karena sesi ini tanpa data kamera."] })] }), _jsxs("div", { className: "report-side", children: [_jsxs("section", { className: "card report-section", children: [_jsx("span", { className: "section-kicker coral", children: "YANG SUDAH BAIK" }), _jsx("h2", { children: "Pertahankan ini" }), r.strengths.length ? r.strengths.map((s, i) => _jsxs("div", { className: "strength", children: [_jsx(CircleCheck, { size: 19 }), _jsx("p", { children: s })] }, i)) : _jsx("p", { className: "muted", children: "Belum ada bukti yang cukup untuk menyimpulkan kekuatan sesi." })] }), _jsxs("section", { className: "card report-section", children: [_jsx("span", { className: "section-kicker green", children: "MAKSIMAL TIGA LANGKAH" }), _jsx("h2", { children: "Coba pada sesi berikutnya" }), r.actions.slice(0, 3).map((a, i) => _jsxs("div", { className: "action-item", children: [_jsx("span", { children: String(i + 1).padStart(2, '0') }), _jsx("p", { children: a })] }, i)), !r.actions.length && _jsx("p", { className: "muted", children: "Catat satu hal yang ingin Anda latih pada sesi berikutnya." })] })] })] }), _jsxs("section", { className: "card transcript-section", id: "transcript", children: [_jsx("div", { className: "section-heading", children: _jsxs("div", { children: [_jsx("span", { className: "section-kicker coral", children: "BUKTI PERCAKAPAN" }), _jsx("h2", { children: "Momen dari sesi" })] }) }), r.moments.length ? r.moments.map((m, i) => _jsxs("div", { id: `moment-${i}`, tabIndex: -1, className: `moment ${active === i ? 'highlighted' : ''}`, children: [_jsx("time", { children: m.at }), _jsxs("div", { children: [_jsx("strong", { children: m.speaker }), _jsxs("p", { children: ["\u201C", m.text, "\u201D"] })] })] }, i)) : _jsx("p", { className: "muted", children: "Belum ada transkrip karena layanan transkripsi tidak terhubung." })] })] });
}
function Setup() {
    const [params] = useSearchParams();
    const navigate = useNavigate();
    const [lesson, setLesson] = useState(() => params.has('subject') ? lessonFromParams(params) : current().lesson);
    const [material, setMaterial] = useState(null);
    const [materialId, setMaterialId] = useState(null);
    const [uploadError, setUploadError] = useState('');
    async function handleFile(f) {
        if (!f)
            return;
        setMaterial(null);
        setUploadError('Memeriksa PDF…');
        try {
            if (f.size === 0 || f.size > 10 * 1024 * 1024 || (!f.name.toLowerCase().endsWith('.pdf')) || (await f.slice(0, 5).text()) !== '%PDF-')
                throw new Error('invalid');
            const uploaded = await api.uploadMaterial(f);
            setUploadError('');
            setMaterial(uploaded.filename);
            setMaterialId(uploaded.id);
        }
        catch (err) {
            setUploadError(err instanceof api.ApiError && err.status !== 400 ? `${err.message} Anda tetap bisa lanjut tanpa materi.` : 'PDF tidak dapat dibaca. Pilih PDF valid maksimal 10 MB atau lanjut tanpa materi.');
        }
    }
    function next() { localStorage.removeItem('gema-draft'); sessionStorage.setItem('gema-current-lesson', JSON.stringify({ lesson, scheduleId: params.get('scheduleId'), material, materialId })); navigate('/simulator/check'); }
    return _jsxs("div", { className: "page flow-page", children: [_jsxs("div", { className: "flow-steps", children: [_jsxs("span", { className: "active", children: ["01 ", _jsx("b", { children: "Persiapan" })] }), _jsxs("span", { children: ["02 ", _jsx("b", { children: "Perangkat" })] }), _jsxs("span", { children: ["03 ", _jsx("b", { children: "Ruang latihan" })] }), _jsxs("span", { children: ["04 ", _jsx("b", { children: "Refleksi" })] })] }), _jsx(PageHeading, { eyebrow: "MULAI SESI BARU", title: "Apa yang ingin Anda latih?", description: "Tentukan konteks pelajaran agar pertanyaan Siswa GeMa terasa relevan." }), _jsxs("div", { className: "setup-layout", children: [_jsxs("section", { className: "card setup-card", children: [_jsx("span", { className: "section-kicker green", children: "KONTEKS PELAJARAN" }), _jsx("h2", { children: "Topik latihan" }), _jsx("p", { className: "muted", children: "Pilihan kurikulum di bawah adalah sampel untuk demo: dua mata pelajaran dan dua bab per mata pelajaran." }), _jsx(LessonFields, { value: lesson, onChange: setLesson }), _jsxs("div", { className: "upload-block", children: [_jsxs("div", { children: [_jsx(Upload, { size: 21 }), _jsxs("strong", { children: ["Materi pendukung ", _jsx("span", { className: "muted", children: "(opsional)" })] })] }), _jsx("p", { children: "PDF diunggah sekali ke server lokal di laptop Anda, lalu dipakai agar pertanyaan murid sesuai isi materi. Video dan layar tidak pernah diunggah." }), _jsxs("label", { className: "file-button", children: ["Pilih PDF", _jsx("input", { type: "file", accept: "application/pdf,.pdf", onChange: e => handleFile(e.target.files?.[0]) })] }), material && _jsxs("span", { className: "file-success", children: [_jsx(CircleCheck, { size: 16 }), " ", material, " \u00B7 nama materi siap"] }), uploadError && _jsx("span", { className: "error-text", role: "status", children: uploadError })] }), _jsxs("div", { className: "setup-footer", children: [_jsx(Button, { to: "/", variant: "subtle", children: "Kembali" }), _jsx(Button, { onClick: next, disabled: uploadError === 'Memeriksa PDF…', icon: ArrowRight, children: "Periksa perangkat" })] })] }), _jsxs("aside", { className: "setup-aside", children: [_jsx("div", { className: "setup-art", children: _jsx("img", { src: image('simulation/teacher-practicing-camera.png'), alt: "Guru berlatih mengajar di depan kamera" }) }), _jsxs("div", { className: "tip-card", children: [_jsx(ShieldCheck, { size: 23 }), _jsxs("div", { children: [_jsx("strong", { children: "Ruang aman untuk mencoba" }), _jsx("p", { children: "Satu Siswa GeMa akan menampilkan pertanyaan contoh sesuai topik. Anda boleh mulai tanpa kamera." })] })] })] })] })] });
}
const current = () => {
    try {
        return JSON.parse(sessionStorage.getItem('gema-current-lesson') || '');
    }
    catch {
        return { lesson: lessons[0], scheduleId: null, material: null };
    }
};
let deviceStream = null;
function DeviceCheck() {
    const navigate = useNavigate();
    const [config] = useState(current);
    const [mic, setMic] = useState(() => deviceStream?.getAudioTracks().some(t => t.readyState === 'live') ? 'ready' : 'idle');
    const [camera, setCamera] = useState(() => deviceStream?.getVideoTracks().some(t => t.readyState === 'live') ? 'ready' : 'off');
    const [message, setMessage] = useState('');
    const video = useRef(null);
    useEffect(() => {
        if (video.current && deviceStream)
            video.current.srcObject = deviceStream;
        return () => { };
    }, [camera]);
    async function requestMic() {
        setMic('checking');
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            deviceStream?.getAudioTracks().forEach(t => { t.stop(); deviceStream?.removeTrack(t); });
            if (deviceStream)
                stream.getAudioTracks().forEach(t => deviceStream?.addTrack(t));
            else
                deviceStream = stream;
            setMic('ready');
            setMessage('Mikrofon siap. Audio tetap di perangkat dalam demo ini.');
        }
        catch {
            setMic('denied');
            setMessage('Akses mikrofon ditolak. Izinkan mikrofon pada pengaturan situs, lalu coba lagi.');
        }
    }
    async function requestCamera() {
        setCamera('checking');
        try {
            const cam = await navigator.mediaDevices.getUserMedia({ video: true });
            if (deviceStream) {
                cam.getVideoTracks().forEach(t => deviceStream?.addTrack(t));
            }
            else
                deviceStream = cam;
            setCamera('ready');
            setMessage('Kamera aktif untuk pratinjau lokal. Video mentah tidak diunggah.');
        }
        catch {
            setCamera('denied');
            setMessage('Kamera tidak tersedia. Anda tetap dapat berlatih hanya dengan audio.');
        }
    }
    function offCamera() { deviceStream?.getVideoTracks().forEach(t => { t.stop(); deviceStream?.removeTrack(t); }); setCamera('off'); }
    function begin() {
        if (mic !== 'ready' || !deviceStream?.getAudioTracks().some(t => t.readyState === 'live')) {
            setMic('idle');
            setMessage('Mikrofon terputus. Periksa lagi sebelum masuk.');
            return;
        }
        deviceStream.getAudioTracks().forEach(t => t.enabled = true);
        sessionStorage.setItem('gema-camera', String(camera === 'ready'));
        navigate('/simulator/room');
    }
    return _jsxs("div", { className: "page flow-page", children: [_jsxs("div", { className: "flow-steps", children: [_jsxs("span", { children: ["01 ", _jsx("b", { children: "Persiapan" })] }), _jsxs("span", { className: "active", children: ["02 ", _jsx("b", { children: "Perangkat" })] }), _jsxs("span", { children: ["03 ", _jsx("b", { children: "Ruang latihan" })] }), _jsxs("span", { children: ["04 ", _jsx("b", { children: "Refleksi" })] })] }), _jsx(PageHeading, { eyebrow: "SEBELUM MASUK", title: "Periksa perangkat Anda", description: `${config.lesson.subject} · ${config.lesson.chapter} · ${config.lesson.kelas}` }), _jsxs("div", { className: "device-layout", children: [_jsxs("section", { className: "camera-preview card", children: [camera === 'ready' ? _jsx("video", { autoPlay: true, muted: true, playsInline: true, ref: video, "aria-label": "Pratinjau kamera Anda" }) : _jsxs("div", { className: "preview-placeholder", children: [_jsx(CameraOff, { size: 34 }), _jsx("strong", { children: "Kamera belum aktif" }), _jsx("span", { children: "Latihan audio saja tetap bisa dilakukan" })] }), _jsx("span", { className: "preview-label", children: "PRATINJAU ANDA" })] }), _jsxs("div", { className: "device-panel card", children: [_jsx("span", { className: "section-kicker green", children: "CEK KESIAPAN" }), _jsx("h2", { children: "Anda memegang kendali." }), _jsx("p", { children: "Dalam demo ini, mikrofon hanya dipakai untuk mengaktifkan ruang latihan. Transkripsi dan penilaian AI belum terhubung." }), _jsxs("div", { className: "device-item", children: [_jsx("span", { className: "device-icon", children: _jsx(Mic, { size: 22 }) }), _jsxs("span", { children: [_jsxs("strong", { children: ["Mikrofon ", _jsx("em", { children: "Wajib" })] }), _jsx("small", { children: mic === 'ready' ? 'Siap digunakan' : mic === 'denied' ? 'Akses ditolak' : 'Belum diperiksa' })] }), _jsx(Button, { onClick: requestMic, disabled: mic === 'checking', variant: mic === 'ready' ? 'subtle' : 'secondary', children: mic === 'ready' ? 'Periksa lagi' : 'Izinkan' })] }), _jsxs("div", { className: "device-item", children: [_jsx("span", { className: "device-icon", children: _jsx(Camera, { size: 22 }) }), _jsxs("span", { children: [_jsxs("strong", { children: ["Kamera ", _jsx("em", { children: "Opsional" })] }), _jsx("small", { children: camera === 'ready' ? 'Pratinjau aktif' : camera === 'denied' ? 'Tidak diizinkan' : 'Anda bisa lanjut tanpa kamera' })] }), camera === 'ready' ? _jsx(Button, { onClick: offCamera, variant: "subtle", children: "Matikan" }) : _jsx(Button, { onClick: requestCamera, disabled: camera === 'checking', variant: "secondary", children: "Aktifkan" })] }), _jsxs("div", { className: "privacy-note", children: [_jsx(ShieldCheck, { size: 21 }), _jsx("span", { children: "Video diproses di perangkat ini dan tidak diunggah. Analisis gerak kamera belum aktif dalam demo." })] }), message && _jsx("div", { className: `notice ${mic === 'denied' ? 'error' : 'neutral'}`, role: "status", children: message }), _jsxs("div", { className: "device-actions", children: [_jsx(Button, { to: lessonUrl(config.lesson, config.scheduleId ?? undefined), variant: "subtle", children: "Kembali" }), _jsx(Button, { onClick: begin, disabled: mic !== 'ready', icon: ArrowRight, children: "Masuk ruang latihan" })] })] })] })] });
}
function readDraft() {
    try {
        const d = JSON.parse(localStorage.getItem('gema-draft') || 'null');
        return d && d.id && d.config && Array.isArray(d.moments) ? d : null;
    }
    catch {
        return null;
    }
}
function useDialogFocus(open, onClose) {
    const close = useRef(onClose);
    close.current = onClose;
    useEffect(() => {
        if (!open)
            return;
        const previous = document.activeElement;
        const dialog = document.querySelector('[role="dialog"],[role="alertdialog"]');
        if (!dialog)
            return;
        const items = () => Array.from(dialog.querySelectorAll('button:not([disabled]),a[href],input,select,textarea,[tabindex="0"]'));
        items()[0]?.focus();
        const handler = (e) => {
            if (e.key === 'Escape' && close.current) {
                e.preventDefault();
                close.current();
            }
            if (e.key === 'Tab') {
                const list = items(), first = list[0], last = list[list.length - 1];
                if (e.shiftKey && document.activeElement === first) {
                    e.preventDefault();
                    last?.focus();
                }
                else if (!e.shiftKey && document.activeElement === last) {
                    e.preventDefault();
                    first?.focus();
                }
            }
        };
        const old = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        const main = document.getElementById('main-content');
        if (dialog.classList.contains('sidebar') && main)
            main.inert = true;
        document.addEventListener('keydown', handler);
        return () => {
            document.body.style.overflow = old;
            if (main)
                main.inert = false;
            document.removeEventListener('keydown', handler);
            previous?.focus();
        };
    }, [open]);
}
function ResumeDraft() {
    const navigate = useNavigate();
    const draft = readDraft();
    if (!draft)
        return null;
    return _jsxs("div", { className: "notice neutral", children: [_jsx(Clock3, { size: 20 }), _jsxs("span", { children: ["Ada latihan ", draft.config.lesson.chapter, " yang belum selesai."] }), _jsx(Button, { onClick: () => { sessionStorage.setItem('gema-current-lesson', JSON.stringify(draft.config)); navigate('/simulator/check'); }, variant: "subtle", children: "Lanjutkan draft" })] });
}
function Reminder() {
    const location = useLocation();
    const schedules = useSchedules();
    const [dismissed, setDismissed] = useState([]);
    const due = schedules.find(s => s.status === 'scheduled' && !s.missed && !dismissed.includes(s.id) && new Date(s.at).getTime() - Date.now() <= 30 * 60 * 1000);
    if (!due || location.pathname === '/simulator/room')
        return null;
    return _jsxs("div", { className: "reminder", role: "status", children: [_jsx(CalendarDays, { size: 22 }), _jsxs("div", { children: [_jsx("strong", { children: "Waktu latihan semakin dekat" }), _jsxs("span", { children: [due.subject, " \u00B7 ", due.chapter, " \u00B7 ", formatTime(due.at), " (waktu lokal)"] })] }), _jsxs(Link, { to: lessonUrl(due, due.id), children: ["Siapkan sesi ", _jsx(ArrowRight, { size: 16 })] }), _jsx("button", { className: "icon-button", "aria-label": "Tutup pengingat", onClick: () => setDismissed([...dismissed, due.id]), children: _jsx(X, { size: 18 }) })] });
}
function TopicCards() { return _jsxs("section", { className: "topic-section", children: [_jsxs("div", { children: [_jsx("span", { className: "section-kicker green", children: "MULAI DARI HAL YANG DEKAT" }), _jsx("h2", { children: "Satu topik kecil untuk hari ini." }), _jsx("p", { className: "muted small", children: "Pilihan materi contoh untuk mencoba GeMa." })] }), _jsx("div", { className: "topic-cards", children: [lessons[1], lessons[2]].map(l => _jsxs(Link, { to: lessonUrl(l), className: `topic-card ${l.subject === 'Biologi' ? 'biology' : ''}`, children: [_jsx("img", { src: image(`subjects/${l.subject === 'Biologi' ? 'biology' : 'mathematics'}-card-portrait.png`), alt: "" }), _jsxs("div", { children: [_jsxs("span", { children: [l.subject, " \u00B7 ", l.kelas] }), _jsx("h3", { children: l.subchapter }), _jsxs("small", { children: ["Siapkan latihan ", _jsx(ArrowRight, { size: 15 })] })] })] }, l.subject)) })] }); }
function Room() {
    const navigate = useNavigate();
    const { store, setStore } = useApp();
    const [draft] = useState(readDraft);
    const [config] = useState(() => draft?.config ?? current());
    const [id] = useState(() => draft?.id ?? crypto.randomUUID());
    const [phase, setPhase] = useState(draft?.phase === 'loading' ? 'error' : draft?.phase ?? 'live');
    const [seconds, setSeconds] = useState(draft?.seconds ?? 0);
    const [paused, setPaused] = useState(Boolean(draft));
    const [camera, setCamera] = useState(Boolean(deviceStream?.getVideoTracks().some(t => t.readyState === 'live')));
    const [micOn, setMicOn] = useState(true);
    const [questionCount, setQuestionCount] = useState(draft?.questionCount ?? 0);
    const [moments, setMoments] = useState(draft?.moments ?? []);
    const [answer, setAnswer] = useState(draft?.answer ?? '');
    const [note, setNote] = useState('');
    const [offline, setOffline] = useState(!navigator.onLine);
    const [chatOpen, setChatOpen] = useState(true);
    const [deviceError, setDeviceError] = useState('');
    const [storageError, setStorageError] = useState(false);
    const [simulateFailure, setSimulateFailure] = useState(false);
    const video = useRef(null);
    const busy = useRef(false);
    const recorder = useRef(null);
    const starting = useRef(null);
    const seen = useRef(new Set());
    const [sessionId, setSessionId] = useState(draft?.sessionId ?? null);
    const [capstone, setCapstone] = useState(draft?.capstone ?? '');
    const [setupError, setSetupError] = useState('');
    const [sendProblem, setSendProblem] = useState('');
    const [recorderReady, setRecorderReady] = useState(false);
    const timer = useRef();
    const liveAt = () => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
    useDialogFocus(phase === 'capstone' || phase === 'error');
    useEffect(() => {
        if (!deviceStream?.getAudioTracks().some(t => t.readyState === 'live')) {
            navigate('/simulator/check', { replace: true });
            return;
        }
        const track = deviceStream.getAudioTracks()[0];
        const ended = () => { setPaused(true); setMicOn(false); setDeviceError('Mikrofon terputus. Periksa kembali perangkat untuk melanjutkan; catatan tetap tersimpan.'); };
        track.addEventListener('ended', ended);
        return () => {
            track.removeEventListener('ended', ended);
            if (timer.current)
                clearTimeout(timer.current);
        };
    }, [navigate]);
    useEffect(() => {
        if (video.current && deviceStream)
            video.current.srcObject = deviceStream;
    }, [camera]);
    // Make the session on the backend once, then listen to the microphone and send numbered pieces of speech.
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                if (!sessionId && !starting.current) {
                    starting.current = (async () => {
                        const list = await api.profiles();
                        const profile = list.find(p => p.subject === config.lesson.subject) ?? list[0];
                        if (!profile)
                            throw new Error('Belum ada profil mata pelajaran di server. Isi SHOW_UNTESTED_PROFILES=true di backend/.env untuk demo.');
                        const created = await api.createSession({ profile_id: profile.id, class_name: config.lesson.kelas, subject: config.lesson.subject, chapter: config.lesson.chapter, sub_chapter: config.lesson.subchapter, material_id: config.materialId ?? null, camera_on: Boolean(deviceStream?.getVideoTracks().length), demo_mode: true });
                        if (config.materialId)
                            api.sendSlide(created.id, 1, 0).catch(() => { });
                        return created.id;
                    })();
                }
                const sid = sessionId ?? await starting.current;
                if (cancelled || !deviceStream)
                    return;
                setSessionId(sid);
                recorder.current = startRecorder(deviceStream, { sessionId: sid, startSeq: draft?.nextSeq ?? 0, offsetMs: (draft?.seconds ?? 0) * 1000, onReply: handleReply, onProblem: m => setSendProblem(m ?? '') });
                setRecorderReady(true);
            }
            catch (err) {
                starting.current = null;
                if (!cancelled)
                    setSetupError(err.message);
            }
        })();
        return () => { cancelled = true; recorder.current?.stop(); recorder.current = null; setRecorderReady(false); };
    }, []);
    useEffect(() => {
        if (paused || offline)
            recorder.current?.pause();
        else
            recorder.current?.resume();
    }, [paused, offline, recorderReady]);
    function handleReply(reply) {
        if (seen.current.has(reply.seq))
            return;
        seen.current.add(reply.seq);
        const mmss = (ms) => `${String(Math.floor(ms / 60000)).padStart(2, '0')}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}`;
        const added = [];
        if (reply.segment)
            added.push({ at: mmss(reply.segment.start_ms), speaker: 'Guru', text: reply.segment.text });
        if (reply.event) {
            added.push({ at: mmss(reply.event.asked_at_ms), speaker: reply.event.persona?.name ?? 'Siswa GeMa', text: reply.event.text });
            if (reply.event.kind !== 'nudge')
                setQuestionCount(x => x + 1);
            setChatOpen(true);
        }
        if (added.length)
            setMoments(prev => [...prev, ...added]);
    }
    useEffect(() => {
        const interval = window.setInterval(() => {
            if (phase === 'live' && !paused && !offline)
                setSeconds(s => s + 1);
        }, 1000);
        return () => clearInterval(interval);
    }, [phase, paused, offline, deviceError]);
    useEffect(() => { const on = () => setOffline(false), off = () => setOffline(true); window.addEventListener('online', on); window.addEventListener('offline', off); return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off); }; }, []);
    useEffect(() => {
        try {
            localStorage.setItem('gema-draft', JSON.stringify({ id, config, seconds, moments, answer, phase, questionCount, sessionId, capstone, nextSeq: recorder.current?.nextSeq() ?? draft?.nextSeq ?? 0 }));
            setStorageError(false);
        }
        catch {
            setStorageError(true);
        }
    }, [id, config, seconds, moments, answer, phase, questionCount]);
    function toggleMic() { const next = !micOn; deviceStream?.getAudioTracks().forEach(t => t.enabled = next); setMicOn(next); }
    async function toggleCamera() {
        if (camera) {
            deviceStream?.getVideoTracks().forEach(t => { t.stop(); deviceStream?.removeTrack(t); });
            setCamera(false);
        }
        else
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                stream.getVideoTracks().forEach(t => deviceStream?.addTrack(t));
                setCamera(true);
            }
            catch {
                setDeviceError('Kamera tidak tersedia. Latihan audio tetap bisa dilanjutkan.');
            }
    }
    async function endLesson() {
        if (phase !== 'live' || busy.current)
            return;
        if (!sessionId) {
            setDeviceError(setupError || 'Sesi belum tersambung ke server. Tunggu sebentar lalu coba lagi.');
            return;
        }
        busy.current = true;
        try {
            await recorder.current?.flush();
            const event = await api.endLesson(sessionId);
            setCapstone(event.text);
            setMoments(prev => [...prev, { at: liveAt(), speaker: event.persona?.name ?? 'Siswa GeMa', text: event.text }]);
            setPhase('capstone');
            setChatOpen(true);
        }
        catch (err) {
            setDeviceError(`Belum bisa mengakhiri sesi: ${err.message}`);
        }
        finally {
            busy.current = false;
        }
    }
    async function finish() {
        if (busy.current)
            return;
        busy.current = true;
        setPhase('loading');
        try {
            if (simulateFailure) {
                setSimulateFailure(false);
                throw new Error('Simulated processing failure');
            }
            await recorder.current?.flush();
            const report = await api.waitForReport(sessionId);
            const all = [...moments, ...(answer.trim() ? [{ at: liveAt(), speaker: 'Guru', text: answer.trim() }] : [])];
            const r = adaptReport(report, { id, lesson: config.lesson, material: config.material, camera, seconds, moments: all });
            const next = { ...store, reports: [r, ...store.reports.filter(x => x.id !== id)], schedules: store.schedules.map(s => s.id === config.scheduleId ? { ...s, status: 'done' } : s) };
            saveStore(next);
            setStore(next);
            localStorage.removeItem('gema-draft');
            recorder.current?.stop();
            recorder.current = null;
            deviceStream?.getTracks().forEach(t => t.stop());
            deviceStream = null;
            navigate(`/report/${id}`);
        }
        catch {
            setPhase('error');
        }
        finally {
            busy.current = false;
        }
    }
    return _jsxs("div", { className: "room-page", children: [_jsxs("div", { className: "room-header", children: [_jsxs("div", { children: [_jsx(Link, { to: "/", className: "room-logo", "aria-label": "Kembali ke Dashboard", children: "g." }), _jsxs("div", { children: [_jsx("strong", { children: "Ruang latihan" }), _jsxs("small", { children: [config.lesson.subject, " \u00B7 ", config.lesson.chapter, " \u00B7 ", config.lesson.kelas] })] })] }), _jsxs("span", { className: "room-state", children: [_jsx(Radio, { size: 15 }), phase === 'live' ? (paused ? 'Dijeda' : 'Sesi berlangsung') : phase === 'capstone' ? 'Pertanyaan akhir' : 'Memproses'] }), _jsxs("span", { className: "room-timer", children: [_jsx(Clock3, { size: 18 }), liveAt()] })] }), (setupError || sendProblem) && _jsx("div", { className: "room-alert", role: "alert", children: setupError || `Audio belum terkirim: ${sendProblem} Mencoba lagi...` }), offline && _jsxs("div", { className: "room-alert", role: "alert", children: [_jsx(WifiOff, { size: 17 }), "Koneksi terputus. Sesi dijeda; catatan lokal tetap ada. ", _jsx("button", { onClick: () => setOffline(!navigator.onLine), children: "Coba sambungkan" })] }), deviceError && _jsxs("div", { className: "room-alert", role: "alert", children: [deviceError, _jsx(Link, { to: "/simulator/check", children: "Periksa perangkat" }), _jsx("button", { onClick: () => setDeviceError(''), children: "Tutup" })] }), storageError && _jsx("div", { className: "room-alert", role: "alert", children: "Penyimpanan lokal gagal. Jangan tutup halaman sebelum sesi berhasil disimpan." }), _jsxs("div", { className: "room-grid", children: [_jsxs("section", { className: "lesson-stage", children: [_jsxs("div", { className: "stage-top", children: [_jsx("span", { className: "stage-kicker", children: "AREA PELAJARAN" }), _jsx("span", { className: "stage-indicator", children: paused ? 'Dijeda' : offline ? 'Menunggu koneksi' : 'Latihan aktif' })] }), _jsxs("div", { className: "stage-center", children: [_jsx("span", { className: "stage-icon", children: _jsx(Sparkles, { size: 33 }) }), _jsx("span", { className: "stage-label", children: "TOPIK HARI INI" }), _jsx("h1", { children: config.lesson.chapter }), _jsx("p", { children: config.lesson.subchapter }), _jsxs("span", { className: "stage-subject", children: [config.lesson.subject, " \u00B7 ", config.lesson.kelas] }), config.material && _jsxs("p", { className: "material-caption", children: ["Nama materi: ", config.material, " \u00B7 isi dipakai untuk pertanyaan"] })] }), _jsxs("div", { className: "stage-bottom", children: [_jsxs("div", { className: "self-view", children: [camera ? _jsx("video", { autoPlay: true, muted: true, playsInline: true, ref: video, "aria-label": "Video diri Anda" }) : _jsxs("div", { children: [_jsx(CameraOff, { size: 21 }), _jsx("small", { children: "Kamera nonaktif" })] }), _jsx("span", { children: "ANDA" })] }), _jsxs("div", { className: "stage-hint", children: [_jsx(ShieldCheck, { size: 18 }), _jsx("span", { children: "Video tetap di perangkat. Analisis kamera belum terhubung." })] })] })] }), _jsxs("aside", { className: `chat-panel ${chatOpen ? '' : 'chat-hidden'}`, children: [_jsxs("div", { className: "chat-header", children: [_jsx("span", { className: "chat-avatar", children: _jsx(Sparkles, { size: 20 }) }), _jsxs("span", { children: [_jsx("strong", { children: "Siswa GeMa" }), _jsx("small", { children: "Satu siswa simulasi \u00B7 pertanyaan teks" })] }), _jsx("button", { className: "icon-button chat-toggle", onClick: () => setChatOpen(!chatOpen), "aria-expanded": chatOpen, "aria-label": chatOpen ? 'Sembunyikan pertanyaan' : 'Tampilkan pertanyaan', children: _jsx(ChevronDown, { size: 20 }) })] }), _jsxs("div", { className: "chat-body", "aria-live": "polite", children: [_jsxs("div", { className: "chat-intro", children: [_jsx(Sparkles, { size: 22 }), _jsx("strong", { children: "Ruang tanya yang aman" }), _jsx("p", { children: "Suara Anda dikirim ke server lokal untuk ditranskripsikan, lalu Siswa GeMa bertanya tentang apa yang baru Anda jelaskan." })] }), moments.map((m, i) => _jsxs("div", { className: `chat-message ${m.speaker === 'Guru' ? 'teacher-note' : ''}`, children: [_jsxs("small", { children: [m.speaker, " \u00B7 ", m.at] }), _jsx("p", { children: m.text })] }, i)), !questionCount && _jsx("p", { className: "waiting-question", children: "Mulai menjelaskan. Pertanyaan pertama muncul setelah sekitar 75 detik bicara." })] }), phase === 'live' && _jsxs("div", { className: "chat-footer", children: [_jsxs("form", { className: "note-form", onSubmit: e => {
                                            e.preventDefault();
                                            if (!note.trim())
                                                return;
                                            setMoments(m => [...m, { at: liveAt(), speaker: 'Guru', text: note.trim() }]);
                                            setNote('');
                                        }, children: [_jsx("label", { htmlFor: "lesson-note", children: "Catatan penjelasan (diketik)" }), _jsx("textarea", { id: "lesson-note", rows: 2, value: note, onChange: e => setNote(e.target.value), placeholder: "Simpan inti penjelasan Anda..." }), _jsx("button", { type: "submit", disabled: !note.trim() || paused, children: "Simpan catatan" })] })] })] })] }), _jsxs("div", { className: "room-controls", children: [_jsxs("div", { className: "control-group", children: [_jsxs("button", { onClick: toggleMic, className: `control ${micOn ? '' : 'control-off'}`, "aria-label": micOn ? 'Matikan mikrofon' : 'Nyalakan mikrofon', "aria-pressed": micOn, children: [micOn ? _jsx(Mic, { size: 20 }) : _jsx(MicOff, { size: 20 }), _jsxs("span", { children: ["Mikrofon ", micOn ? 'aktif' : 'mati'] })] }), _jsxs("button", { onClick: toggleCamera, className: "control", "aria-label": camera ? 'Matikan kamera' : 'Nyalakan kamera', "aria-pressed": camera, children: [camera ? _jsx(Camera, { size: 20 }) : _jsx(CameraOff, { size: 20 }), _jsxs("span", { children: ["Kamera ", camera ? 'aktif' : 'mati'] })] }), _jsxs("button", { onClick: () => setPaused(!paused), className: "control", disabled: phase !== 'live' || offline || !deviceStream?.getAudioTracks().some(t => t.readyState === 'live'), "aria-label": paused ? 'Lanjutkan sesi' : 'Jeda sesi', children: [paused ? _jsx(Play, { size: 20 }) : _jsx(Pause, { size: 20 }), _jsx("span", { children: paused ? 'Lanjutkan' : 'Jeda' })] })] }), _jsxs("button", { className: "end-button", onClick: endLesson, disabled: phase !== 'live', children: [_jsx(Square, { size: 18, fill: "currentColor" }), " Selesai mengajar"] })] }), _jsxs("div", { className: "room-disclaimer", children: ["MODE DEMO \u00B7 Tidak merekam suara atau video. Transkripsi, AI, dan analisis kamera belum terhubung.", _jsxs("details", { children: [_jsx("summary", { children: "Uji ketahanan demo" }), _jsxs("label", { children: [_jsx("input", { type: "checkbox", checked: simulateFailure, onChange: e => setSimulateFailure(e.target.checked) }), " Simulasikan satu kegagalan pemrosesan"] })] })] }), phase === 'capstone' && _jsx("div", { className: "modal-backdrop", children: _jsxs("div", { className: "modal capstone-modal", role: "dialog", "aria-modal": "true", "aria-labelledby": "capstone-title", children: [_jsx("span", { className: "section-kicker coral", children: "CAPSTONE INQUIRY \u00B7 1 PERTANYAAN" }), _jsx("h2", { id: "capstone-title", children: "Satu pertanyaan terakhir." }), _jsx("p", { children: capstone }), _jsxs("label", { children: ["Catatan jawaban Anda ", _jsx("span", { className: "muted", children: "(opsional; jawaban lisan Anda sudah direkam)" }), _jsx("textarea", { rows: 4, value: answer, onChange: e => setAnswer(e.target.value), placeholder: "Tuliskan inti jawaban untuk disimpan bersama sesi..." })] }), _jsx(Button, { onClick: finish, icon: ArrowRight, children: "Simpan sesi & lihat refleksi" })] }) }), phase === 'loading' && _jsx("div", { className: "modal-backdrop", children: _jsxs("div", { className: "modal loading-modal", role: "status", children: [_jsx("img", { src: image('ui-states/loading-lesson-preparation.png'), alt: "" }), _jsx("h2", { children: "Menyiapkan refleksi..." }), _jsx("p", { children: "Menyusun laporan dari transkrip Anda. Biasanya 10-40 detik." }), _jsx("div", { className: "loading-bar" })] }) }), phase === 'error' && _jsx("div", { className: "modal-backdrop", children: _jsxs("div", { className: "modal", role: "alertdialog", "aria-modal": "true", "aria-labelledby": "save-error-title", children: [_jsx(AlertCircle, { size: 26 }), _jsx("h2", { id: "save-error-title", children: "Sesi belum tersimpan" }), _jsx("p", { children: "Catatan masih ada. Coba lagi untuk menyimpan satu laporan yang sama." }), _jsx(Button, { onClick: finish, icon: RefreshCw, children: "Coba lagi" })] }) })] });
}
createRoot(document.getElementById('root')).render(_jsx(React.StrictMode, { children: _jsx(App, {}) }));
