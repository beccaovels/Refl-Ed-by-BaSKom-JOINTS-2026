import { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext.js';

// A planned practice is "terlewat" (missed) only when its time has passed and the teacher never started it. Starting it
// ties a session to it (`sessionId`, as `session_id` in the API contract's schedule), and finishing marks it done.
// Judging by the clock alone made a practice flip to "Terlewat" in the middle of being practised on time.
export const isMissed = (s, now) => s.status === 'scheduled' && !s.sessionId && new Date(s.at).getTime() < now;

export const scheduleLabel = (s) =>
    s.status === 'done' ? 'Selesai' : s.missed ? 'Terlewat' : s.sessionId ? 'Dimulai' : 'Terjadwal';

export function useSchedules() {
    const { store } = useApp();
    const [now, setNow] = useState(Date.now());
    useEffect(() => {
        const timer = setInterval(() => setNow(Date.now()), 15000);
        return () => clearInterval(timer);
    }, []);
    return store.schedules
        .map((s) => ({ ...s, missed: isMissed(s, now) }))
        .sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
}
