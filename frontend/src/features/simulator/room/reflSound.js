// The little chime Refl makes when a question pops up. Made with the Web Audio API, so there is no sound file to
// ship and no library to add.
//
// Browsers only let a page make sound after the person has used it, so the context is created lazily and, if the
// browser still holds it back, the chime is simply skipped: a missing sound never breaks the room. The teacher can
// also switch it off; the choice is remembered.
const KEY = 'baskom-refl-sound';
const STALE_MS = 1000; // a chime that could not start within this long is dropped
const LEVEL = 0.07; // quiet on purpose: the microphone is listening too, and the teacher is talking

let context = null;
let unlockBound = false;

const AudioContextClass = typeof window === 'undefined' ? null : window.AudioContext || window.webkitAudioContext;

export function isSoundOn() {
    try {
        return localStorage.getItem(KEY) !== 'off';
    } catch {
        return true;
    }
}

export function setSoundOn(on) {
    try {
        localStorage.setItem(KEY, on ? 'on' : 'off');
    } catch {
        /* the choice only lasts for this visit */
    }
}

/** Create the audio context on the first tap or key press, which is when browsers allow it to start. */
export function unlockSoundOnFirstUse() {
    if (!AudioContextClass || unlockBound) return;
    unlockBound = true;
    const unlock = () => {
        try {
            context ??= new AudioContextClass();
            context.resume?.();
        } catch {
            /* no audio on this device */
        }
        window.removeEventListener('pointerdown', unlock);
        window.removeEventListener('keydown', unlock);
    };
    window.addEventListener('pointerdown', unlock);
    window.addEventListener('keydown', unlock);
}

// Two quick rising notes, "pi-pii": soft triangle waves that slide up a little and fade out.
const NOTES = [
    { at: 0, from: 523.25, to: 659.25, length: 0.11 },
    { at: 0.1, from: 783.99, to: 1174.66, length: 0.17 },
];

function chime() {
    const start = context.currentTime + 0.01;
    for (const note of NOTES) {
        const oscillator = context.createOscillator();
        const gain = context.createGain();
        const from = start + note.at;
        oscillator.type = 'triangle';
        oscillator.frequency.setValueAtTime(note.from, from);
        oscillator.frequency.exponentialRampToValueAtTime(note.to, from + note.length * 0.8);
        gain.gain.setValueAtTime(0.0001, from);
        gain.gain.exponentialRampToValueAtTime(LEVEL, from + 0.015);
        gain.gain.exponentialRampToValueAtTime(0.0001, from + note.length);
        oscillator.connect(gain).connect(context.destination);
        oscillator.start(from);
        oscillator.stop(from + note.length + 0.02);
    }
}

/** Play the chime once. Does nothing when the sound is off, unavailable, or the browser has not allowed it yet. */
export function playReflChime() {
    if (!AudioContextClass || !isSoundOn()) return;
    try {
        context ??= new AudioContextClass();
        if (context.state === 'running') {
            chime();
            return;
        }
        // Held back by the browser: try to wake it, but never play a chime that is late. A question from a minute ago
        // must not ring when the teacher finally taps the page.
        const asked = performance.now();
        context.resume().then(() => context.state === 'running' && performance.now() - asked < STALE_MS && chime(), () => {});
    } catch {
        /* audio is unavailable: stay quiet */
    }
}
