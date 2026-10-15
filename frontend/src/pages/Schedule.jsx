import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { CalendarDays, ChevronLeft, ChevronRight, CircleCheck, Plus, X, ArrowRight, AlertCircle } from 'lucide-react';
import { useApp } from '../context/AppContext.js';
import { Button } from '../components/Button.jsx';
import { Empty } from '../components/Empty.jsx';
import { PageHeading } from '../components/PageHeading.jsx';
import { LessonFields } from '../components/LessonFields.jsx';
import { useDialogFocus } from '../hooks/useDialogFocus.js';
import { scheduleLabel, useSchedules } from '../hooks/useSchedules.js';
import { lessonUrl } from '../lib/lesson.js';
import { formatDate, formatTime, lessons, lessonFromParams } from '../lib/data.js';
import { APP_NAME } from '../lib/config.js';

export function Schedule() {
    const { store, setStore } = useApp();
    const navigate = useNavigate();
    const [params, setParams] = useSearchParams();
    const schedules = useSchedules();
    const [month, setMonth] = useState(() => new Date());
    const [selected, setSelected] = useState(() => new Date());
    const [editing, setEditing] = useState(null);
    const [showForm, setShowForm] = useState(params.has('subject'));
    const [lesson, setLesson] = useState(() => lessonFromParams(params));
    const [date, setDate] = useState(() => {
        const d = new Date(Date.now() + 86400000);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    });
    const [time, setTime] = useState('10:00');
    const [error, setError] = useState('');
    const first = new Date(month.getFullYear(), month.getMonth(), 1);
    const offset = (first.getDay() + 6) % 7;
    const days = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
    const dateKey = (d) =>
        `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    function openForm(item) {
        setEditing(item ?? null);
        setLesson(
            item
                ? {
                      kelas: item.kelas,
                      subject: item.subject,
                      chapter: item.chapter,
                      subchapter: item.subchapter,
                  }
                : lessons[0],
        );
        setDate(item ? dateKey(new Date(item.at)) : dateKey(selected));
        setTime(
            item
                ? `${String(new Date(item.at).getHours()).padStart(2, '0')}:${String(new Date(item.at).getMinutes()).padStart(2, '0')}`
                : '10:00',
        );
        setError('');
        setShowForm(true);
    }
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
        const item = {
            id: editing?.id ?? crypto.randomUUID(),
            ...lesson,
            at: at.toISOString(),
            status: 'scheduled',
        };
        setStore((prev) => ({
            ...prev,
            schedules: editing
                ? prev.schedules.map((s) => (s.id === editing.id ? item : s))
                : [...prev.schedules, item],
        }));
        setShowForm(false);
        setParams({});
        setSelected(at);
        setMonth(at);
    }
    const candidate = date && time ? new Date(`${date}T${time}`).getTime() : 0;
    const overlap = store.schedules.some(
        (s) =>
            s.id !== editing?.id &&
            s.status === 'scheduled' &&
            Math.abs(new Date(s.at).getTime() - candidate) < 60 * 60 * 1000,
    );
    const upcoming = schedules.filter((s) => !s.missed && s.status === 'scheduled');
    const missed = schedules.filter((s) => s.missed);
    const monthLabel = formatDate(first, {
        month: 'long',
        year: 'numeric',
    });
    useDialogFocus(showForm, () => setShowForm(false));
    return (
        <div className="page">
            <PageHeading
                title="Jadwal latihan"
                description="Sisihkan waktu yang pas. Setiap jadwal membawa topik langsung ke ruang latihan."
                action={
                    <Button onClick={() => openForm()} icon={Plus}>
                        Jadwalkan latihan
                    </Button>
                }
            />
            <div className="schedule-layout">
                <section className="card calendar-card">
                    <div className="calendar-top">
                        <div>
                            <h2>{monthLabel}</h2>
                        </div>
                        <div className="month-actions">
                            <button
                                className="icon-button"
                                aria-label="Bulan sebelumnya"
                                onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
                            >
                                <ChevronLeft />
                            </button>
                            <button
                                className="icon-button"
                                aria-label="Bulan berikutnya"
                                onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
                            >
                                <ChevronRight />
                            </button>
                        </div>
                    </div>
                    <div className="calendar-grid weekdays">
                        {['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'].map((x) => (
                            <span key={x}>{x}</span>
                        ))}
                    </div>
                    <div className="calendar-grid days">
                        {Array.from(
                            {
                                length: offset,
                            },
                            (_, i) => (
                                <span key={`blank-${i}`} />
                            ),
                        )}
                        {Array.from(
                            {
                                length: days,
                            },
                            (_, i) => {
                                const d = new Date(month.getFullYear(), month.getMonth(), i + 1),
                                    k = dateKey(d),
                                    count = schedules.filter((s) => dateKey(new Date(s.at)) === k).length;
                                return (
                                    <button
                                        className={`day ${dateKey(selected) === k ? 'selected' : ''} ${dateKey(new Date()) === k ? 'today' : ''}`}
                                        onClick={() => setSelected(d)}
                                        aria-pressed={dateKey(selected) === k}
                                        aria-label={`${formatDate(d.toISOString())}, ${count} sesi`}
                                        key={k}
                                    >
                                        <span>{i + 1}</span>
                                        {count > 0 && <span className="calendar-dot" />}
                                    </button>
                                );
                            },
                        )}
                    </div>
                    <div className="selected-day">
                        <h3>
                            {formatDate(selected.toISOString(), {
                                weekday: 'long',
                                day: 'numeric',
                                month: 'long',
                            })}
                        </h3>
                        {schedules
                            .filter((s) => dateKey(new Date(s.at)) === dateKey(selected))
                            .map((s) => (
                                <Link to={lessonUrl(s, s.id)} key={s.id}>
                                    {formatTime(s.at)}
                                    {' · '}
                                    {s.subject}
                                    {' — '}
                                    {s.chapter}
                                    <span className="status">{scheduleLabel(s)}</span>
                                </Link>
                            ))}
                        {!schedules.some((s) => dateKey(new Date(s.at)) === dateKey(selected)) && (
                            <p className="muted small">Belum ada latihan pada tanggal ini.</p>
                        )}
                    </div>
                    <div className="calendar-footer">
                        <span>
                            <span className="calendar-dot" />
                            {' Ada latihan'}
                        </span>
                        <Button onClick={() => openForm()} variant="subtle" icon={Plus}>
                            {'Tambah di '}
                            {formatDate(selected.toISOString(), {
                                day: 'numeric',
                                month: 'long',
                            })}
                        </Button>
                    </div>
                </section>
                <section className="card upcoming-card">
                    <div className="section-heading">
                        <div>
                            <h2>Latihan mendatang</h2>
                        </div>
                        <span className="count-pill">
                            {upcoming.length}
                            {' sesi'}
                        </span>
                    </div>
                    {upcoming.length ? (
                        <div className="upcoming-list">
                            {upcoming.map((s) => (
                                <div className="upcoming-item" key={s.id}>
                                    <div className="upcoming-icon">
                                        <CalendarDays size={20} />
                                    </div>
                                    <div className="upcoming-copy">
                                        <strong>
                                            {s.subject}
                                            {' · '}
                                            {s.chapter}
                                        </strong>
                                        <small>
                                            {s.subchapter}
                                            {' · '}
                                            {s.kelas}
                                        </small>
                                        <small>
                                            {formatDate(s.at, {
                                                weekday: 'long',
                                                day: 'numeric',
                                                month: 'short',
                                            })}
                                            {' · '}
                                            {formatTime(s.at)}
                                            {' (waktu lokal)'}
                                        </small>
                                        <div className="inline-actions">
                                            <button onClick={() => navigate(lessonUrl(s, s.id))}>
                                                {'Mulai sesi '}
                                            </button>
                                            <button onClick={() => openForm(s)}>Ubah</button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <Empty
                            title="Belum ada sesi"
                            body="Buat jadwal pertama agar waktu latihan terasa lebih mudah dijaga."
                            art="schedule/upcoming-teaching-session.png"
                            action={
                                <Button onClick={() => openForm()} variant="secondary" icon={Plus}>
                                    Buat jadwal
                                </Button>
                            }
                        />
                    )}
                </section>
            </div>
            {missed.length > 0 && (
                <section className="card missed-card">
                    <h2>Sesi terlewat</h2>
                    <p className="muted">Waktu telah lewat, tetapi rencana latihan Anda tetap tersimpan.</p>
                    {missed.map((s) => (
                        <div className="missed-row" key={s.id}>
                            <span>
                                <strong>
                                    {s.subject}
                                    {' · '}
                                    {s.chapter}
                                </strong>
                                <small>
                                    {formatDate(s.at)}
                                    {' · '}
                                    {formatTime(s.at)}
                                    {' (waktu lokal)'}
                                </small>
                            </span>
                            <span className="status status-warn">Terlewat</span>
                            <Button onClick={() => openForm(s)} variant="subtle">
                                Jadwalkan ulang
                            </Button>
                        </div>
                    ))}
                </section>
            )}
            {showForm && (
                <div
                    className="modal-backdrop"
                    onMouseDown={(e) => {
                        if (e.target === e.currentTarget) setShowForm(false);
                    }}
                >
                    <div className="modal" role="dialog" aria-modal="true" aria-labelledby="schedule-title">
                        <div className="modal-head">
                            <div>
                                <h2 id="schedule-title">{editing ? 'Ubah jadwal' : 'Jadwalkan latihan'}</h2>
                            </div>
                            <button
                                className="icon-button"
                                aria-label="Tutup formulir"
                                onClick={() => setShowForm(false)}
                            >
                                <X />
                            </button>
                        </div>
                        <form onSubmit={save}>
                            <LessonFields value={lesson} onChange={setLesson} />
                            <div className="field-grid">
                                <label>
                                    Tanggal
                                    <input
                                        type="date"
                                        value={date}
                                        onChange={(e) => setDate(e.target.value)}
                                        required
                                    />
                                </label>
                                <label>
                                    Jam (waktu lokal)
                                    <input
                                        type="time"
                                        value={time}
                                        onChange={(e) => setTime(e.target.value)}
                                        required
                                    />
                                </label>
                            </div>
                            {overlap && (
                                <div className="notice warning">
                                    <AlertCircle size={18} />
                                    <span>
                                        Ada jadwal lain dalam rentang satu jam. Anda tetap dapat menyimpan keduanya.
                                    </span>
                                </div>
                            )}
                            {error && (
                                <div className="notice error" role="alert">
                                    <AlertCircle size={18} />
                                    {error}
                                </div>
                            )}
                            <div className="modal-actions">
                                <Button onClick={() => setShowForm(false)} variant="subtle">
                                    Batal
                                </Button>
                                <Button type="submit" icon={CircleCheck}>
                                    Simpan jadwal
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
