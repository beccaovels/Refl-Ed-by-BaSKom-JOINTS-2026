// Refl, the one character who asks the teacher questions in the simulator room.
//
// Refl pops up in the bottom-right corner when there is something to say, with a chatbox that holds the question.
// There is no permanent chat panel: when the teacher is done reading, Refl tucks away into a small round button
// and comes back (with a new pose and a short chime) the next time a question arrives.
//
// What used to live in the chat panel is still here: the questions and the earlier ones, the first-use hint, and
// the typed note. Refl never takes keyboard focus on its own, because the teacher is in the middle of a lesson.
import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, NotebookPen, Volume2, VolumeX, X } from 'lucide-react';
import { REFL_NAME } from '../../../lib/config.js';
import { isSoundOn, playReflChime, setSoundOn, unlockSoundOnFirstUse } from './reflSound.js';

const AUTO_HIDE_MS = 9000; // a passing remark (not a question) tucks itself away after this long

// What Refl is doing, by the kind of event the backend sent.
const KINDS = {
    regular: { label: 'bertanya', question: true },
    misconception: { label: 'bertanya', question: true },
    answer: { label: 'menjawab', question: false },
    reaction: { label: 'menanggapi', question: false },
    nudge: { label: 'menunggu Anda', question: false },
};
// Events saved before kinds were recorded (a resumed draft) are shown as plain questions.
const kindOf = (m) => KINDS[m.kind] ?? KINDS.regular;
// A follow-up is a question too, even though it arrives as a reaction.
const asksSomething = (m) => kindOf(m).question || (m.kind === 'reaction' && m.satisfied === false);
const labelOf = (m) => (m.kind === 'reaction' && m.satisfied === false ? 'bertanya lagi' : kindOf(m).label);
const keyOf = (m) => m.id ?? `${m.at}|${m.text}`;
// The capstone question has its own dialog; typed notes and the teacher's speech are not Refl's.
const fromRefl = (m) => m.speaker !== 'Guru' && m.kind !== 'capstone';

const sprite = (pose) => `./assets/refl-ask-${pose}.svg`;

// Refl sits in the bottom-right corner but must never cover the controls (Selesai mengajar is at the right end), so
// it rests just above the row of controls wherever that row is on this screen.
function useAboveControls() {
    const [bottom, setBottom] = useState(96);
    useEffect(() => {
        const measure = () => {
            const controls = document.querySelector('.room-controls');
            if (!controls) return;
            setBottom(Math.max(12, Math.round(window.innerHeight - controls.getBoundingClientRect().top + 12)));
        };
        measure();
        window.addEventListener('resize', measure);
        window.addEventListener('scroll', measure, { passive: true });
        const observer = new ResizeObserver(measure);
        observer.observe(document.body);
        return () => {
            window.removeEventListener('resize', measure);
            window.removeEventListener('scroll', measure);
            observer.disconnect();
        };
    }, []);
    return bottom;
}

export function ReflPopup({ moments, live, paused, onAddNote }) {
    const messages = useMemo(() => moments.filter(fromRefl), [moments]);
    const latest = messages[messages.length - 1] ?? null;
    const [open, setOpen] = useState(false);
    const [pose, setPose] = useState(2); // the first time Refl appears the pose flips to 1, then they take turns
    const [appearances, setAppearances] = useState(0);
    const [read, setRead] = useState(messages.length); // how many messages the teacher has had on screen
    const [notesOpen, setNotesOpen] = useState(false);
    const [note, setNote] = useState('');
    const [engaged, setEngaged] = useState(false); // the pointer or keyboard is inside: do not tuck away
    const [soundOn, setSound] = useState(isSoundOn);
    const seen = useRef(new Set(messages.map(keyOf))); // a resumed lesson does not replay what was already asked
    const launcher = useRef(null);
    const card = useRef(null);
    const greeted = useRef(false);
    const bottom = useAboveControls();

    useEffect(unlockSoundOnFirstUse, []);

    function appear() {
        setPose((p) => (p === 1 ? 2 : 1));
        setAppearances((n) => n + 1);
        setOpen(true);
    }

    // At the start of a lesson Refl says hello once (no chime: it is not a question), so the teacher knows where it is.
    useEffect(() => {
        if (!live || messages.length > 0 || greeted.current) return;
        greeted.current = true; // once, even when the effect runs twice in development
        appear();
    }, [live]);

    // A new message: Refl pops up, and chimes once if it is a question.
    useEffect(() => {
        const fresh = messages.filter((m) => !seen.current.has(keyOf(m)));
        if (!fresh.length) return;
        fresh.forEach((m) => seen.current.add(keyOf(m)));
        if (!live) return;
        appear();
        if (fresh.some(asksSomething)) playReflChime();
    }, [messages]);

    // Having Refl on screen counts as reading what it says.
    useEffect(() => {
        if (open) setRead(messages.length);
    }, [open, messages.length]);

    // A passing remark tucks itself away; a question stays until the teacher is done with it.
    const keepOpen = (latest && asksSomething(latest)) || engaged || notesOpen || note.trim() !== '';
    useEffect(() => {
        if (!open || keepOpen) return;
        const timer = setTimeout(() => setOpen(false), AUTO_HIDE_MS);
        return () => clearTimeout(timer);
    }, [open, keepOpen, latest]);

    if (!live) return null;

    const unread = Math.max(0, messages.length - read);
    const earlier = messages.slice(0, -1);

    function hide() {
        const hadFocus = card.current?.contains(document.activeElement);
        setOpen(false);
        setEngaged(false);
        if (hadFocus) requestAnimationFrame(() => launcher.current?.focus());
    }

    function toggleSound() {
        const next = !soundOn;
        setSound(next);
        setSoundOn(next);
        if (next) playReflChime(); // so the teacher hears what they just switched on
    }

    if (!open)
        return (
            <div className="refl-launcher-wrap" style={{ bottom }}>
                <button
                    ref={launcher}
                    type="button"
                    className={`refl-launcher ${unread ? 'has-unread' : ''}`}
                    onClick={appear}
                    aria-label={unread ? `Buka ${REFL_NAME}, ${unread} pesan baru` : `Buka ${REFL_NAME}`}
                >
                    <img src={sprite(pose)} alt="" draggable="false" />
                </button>
                {unread > 0 && (
                    <span className="refl-badge" aria-hidden="true">
                        {unread}
                    </span>
                )}
            </div>
        );

    return (
        <aside
            className="refl"
            style={{ bottom }}
            aria-label={REFL_NAME}
            onMouseEnter={() => setEngaged(true)}
            onMouseLeave={() => setEngaged(false)}
            onFocus={() => setEngaged(true)}
            onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && setEngaged(false)}
            onKeyDown={(e) => e.key === 'Escape' && hide()}
        >
            <img key={appearances} className="refl-character" src={sprite(pose)} alt="" draggable="false" />
            <div className="refl-card" ref={card}>
                <div className="refl-head">
                    <strong>{REFL_NAME}</strong>
                    <span>{latest ? labelOf(latest) : 'menyapa'}</span>
                    <button
                        type="button"
                        className="icon-button"
                        onClick={toggleSound}
                        aria-pressed={soundOn}
                        aria-label={soundOn ? 'Matikan suara Refl' : 'Nyalakan suara Refl'}
                        title={soundOn ? 'Suara Refl menyala' : 'Suara Refl mati'}
                    >
                        {soundOn ? <Volume2 size={16} /> : <VolumeX size={16} />}
                    </button>
                    <button type="button" className="icon-button" onClick={hide} aria-label={`Sembunyikan ${REFL_NAME}`}>
                        <X size={16} />
                    </button>
                </div>

                <div className="refl-body" aria-live="polite">
                    {latest ? (
                        <div className="refl-bubble">
                            <p>{latest.text}</p>
                            <small>{latest.at}</small>
                        </div>
                    ) : (
                        <div className="refl-bubble">
                            <p>{`Halo, saya ${REFL_NAME}! Mulai menjelaskan, ya. Pertanyaan pertama muncul setelah sekitar 75 detik bicara.`}</p>
                            <small>Suara Anda dikirim ke server lokal untuk ditranskripsikan; saya bertanya tentang apa yang baru Anda jelaskan.</small>
                        </div>
                    )}

                    {earlier.length > 0 && (
                        <details className="refl-earlier">
                            <summary>
                                {`Sebelumnya (${earlier.length})`}
                                <ChevronDown size={14} />
                            </summary>
                            <ul>
                                {[...earlier].reverse().map((m) => (
                                    <li key={keyOf(m)}>
                                        <small>
                                            {labelOf(m)}
                                            {' · '}
                                            {m.at}
                                        </small>
                                        <p>{m.text}</p>
                                    </li>
                                ))}
                            </ul>
                        </details>
                    )}
                </div>

                <div className="refl-notes">
                    <button
                        type="button"
                        className="refl-notes-toggle"
                        aria-expanded={notesOpen}
                        aria-controls="refl-note-form"
                        onClick={() => setNotesOpen((v) => !v)}
                    >
                        <NotebookPen size={15} />
                        Tulis catatan
                    </button>
                    {notesOpen && (
                        <form
                            id="refl-note-form"
                            className="note-form"
                            onSubmit={(e) => {
                                e.preventDefault();
                                if (!note.trim()) return;
                                onAddNote(note.trim());
                                setNote('');
                            }}
                        >
                            <label htmlFor="lesson-note">Catatan penjelasan (diketik)</label>
                            <textarea
                                id="lesson-note"
                                rows={2}
                                value={note}
                                onChange={(e) => setNote(e.target.value)}
                                placeholder="Simpan inti penjelasan Anda..."
                            />
                            <button type="submit" disabled={!note.trim() || paused}>
                                Simpan catatan
                            </button>
                        </form>
                    )}
                </div>
            </div>
        </aside>
    );
}
