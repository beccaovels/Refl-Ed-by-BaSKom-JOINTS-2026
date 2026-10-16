import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { CalendarDays, X, ArrowRight } from 'lucide-react';
import { useSchedules } from '../hooks/useSchedules.js';
import { lessonUrl } from '../lib/lesson.js';
import { formatTime } from '../lib/data.js';

export function Reminder() {
    const location = useLocation();
    const schedules = useSchedules();
    const [dismissed, setDismissed] = useState([]);
    const due = schedules.find(
        (s) =>
            s.status === 'scheduled' &&
            !s.sessionId &&
            !s.missed &&
            !dismissed.includes(s.id) &&
            new Date(s.at).getTime() - Date.now() <= 30 * 60 * 1000,
    );
    if (!due || location.pathname === '/simulator/room') return null;
    return (
        <div className="reminder">
            <div className="notice-card is-reminder" role="status">
                <CalendarDays size={22} />
                <div className="notice-copy">
                    <strong>Waktu latihan semakin dekat</strong>
                    <span>{`${due.subject} · ${due.chapter} · ${formatTime(due.at)} (waktu lokal)`}</span>
                </div>
                <div className="notice-actions">
                    <Link className="button button-secondary" to={lessonUrl(due, due.id)}>
                        <span>Siapkan sesi</span>
                        <ArrowRight size={16} />
                    </Link>
                    <button
                        className="icon-button"
                        aria-label="Tutup pengingat"
                        onClick={() => setDismissed([...dismissed, due.id])}
                    >
                        <X size={18} />
                    </button>
                </div>
            </div>
        </div>
    );
}
