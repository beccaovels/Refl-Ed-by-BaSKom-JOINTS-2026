// Microphone to numbered WAV pieces, cut at the teacher's pauses (docs/api-contract.md, Audio).
// Audio stays in memory; each piece is sent once and forgotten. Video is never touched here.
import { ApiError, sendAudio } from './api.js';

const RATE = 16000;
const SPEECH_RMS = 0.012; // below this a frame counts as silence
const END_OF_PIECE_MS = 800; // this much silence after speech ends a piece
const MIN_SPEECH_MS = 500; // shorter bursts are noise and are dropped
const MAX_PIECE_MS = 25000;
const HEARTBEAT_MS = 30000; // the backend only notices silence when something arrives, so send a tiny silent piece
const PREROLL_MS = 250;

function resample(samples, from) {
    if (from === RATE)
        return samples;
    const out = new Float32Array(Math.round(samples.length * RATE / from));
    const ratio = from / RATE;
    for (let i = 0; i < out.length; i++) {
        const pos = i * ratio, i0 = Math.floor(pos), i1 = Math.min(i0 + 1, samples.length - 1);
        out[i] = samples[i0] + (samples[i1] - samples[i0]) * (pos - i0);
    }
    return out;
}

export function encodeWav(chunks, fromRate) {
    const total = chunks.reduce((n, c) => n + c.length, 0);
    const joined = new Float32Array(total);
    let at = 0;
    for (const c of chunks) {
        joined.set(c, at);
        at += c.length;
    }
    const pcm = resample(joined, fromRate);
    const view = new DataView(new ArrayBuffer(44 + pcm.length * 2));
    const text = (o, s) => [...s].forEach((ch, i) => view.setUint8(o + i, ch.charCodeAt(0)));
    text(0, 'RIFF');
    view.setUint32(4, 36 + pcm.length * 2, true);
    text(8, 'WAVEfmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // mono
    view.setUint32(24, RATE, true);
    view.setUint32(28, RATE * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    text(36, 'data');
    view.setUint32(40, pcm.length * 2, true);
    pcm.forEach((s, i) => view.setInt16(44 + i * 2, Math.max(-1, Math.min(1, s)) * 0x7fff, true));
    return new Blob([view], { type: 'audio/wav' });
}

/**
 * Start listening. `offsetMs` is how much of the lesson has already happened (when resuming a draft)
 * and `startSeq` the next piece number, so a resumed lesson never reuses a number.
 * onReply(reply) gets each backend reply; onProblem(message | null) reports trouble sending.
 */
export function startRecorder(stream, { sessionId, startSeq = 0, offsetMs = 0, onReply, onProblem }) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    let ctx;
    try {
        ctx = new AudioCtx({ sampleRate: RATE });
    }
    catch {
        ctx = new AudioCtx();
    }
    ctx.resume?.();
    const source = ctx.createMediaStreamSource(stream);
    const processor = ctx.createScriptProcessor(4096, 1, 1);
    const mute = ctx.createGain();
    mute.gain.value = 0; // the processor must be connected to run, but nothing should play back
    source.connect(processor);
    processor.connect(mute);
    mute.connect(ctx.destination);

    const t0 = performance.now();
    let pausedTotal = 0, pausedAt = null, stopped = false;
    const now = () => offsetMs + (pausedAt ?? performance.now()) - t0 - pausedTotal;

    let seq = startSeq, piece = null, preroll = null, lastActivity = now();
    const queue = [];
    let sending = false;

    function enqueue(startMs, endMs, chunks) {
        queue.push({ seq: seq++, startMs, endMs: Math.max(endMs, startMs), wav: encodeWav(chunks, ctx.sampleRate) });
        drain();
    }
    async function drain() {
        if (sending)
            return;
        sending = true;
        while (queue.length) {
            const job = queue[0];
            try {
                onReply(await sendAudio(sessionId, job.seq, job.startMs, job.endMs, job.wav));
                queue.shift();
                onProblem(null);
            }
            catch (err) {
                const retry = !(err instanceof ApiError) || err.status === 0 || err.status === 409 || err.status >= 500;
                if (!retry || stopped) {
                    queue.shift(); // a piece the backend will never accept, or we are leaving: do not block the rest
                    if (!stopped)
                        onProblem(err.message);
                    continue;
                }
                onProblem(err.message);
                await new Promise(r => setTimeout(r, 2000)); // same seq again: the backend ignores a repeat
            }
        }
        sending = false;
    }
    function endPiece() {
        if (!piece)
            return;
        const done = piece;
        piece = null;
        if (done.speechMs >= MIN_SPEECH_MS) {
            enqueue(done.startMs, done.lastSpeechMs, done.chunks);
            lastActivity = now();
        }
    }

    processor.onaudioprocess = (event) => {
        if (stopped || pausedAt !== null)
            return;
        const frame = new Float32Array(event.inputBuffer.getChannelData(0));
        const frameMs = frame.length / ctx.sampleRate * 1000;
        const t = now();
        let sum = 0;
        for (const s of frame)
            sum += s * s;
        const speaking = Math.sqrt(sum / frame.length) > SPEECH_RMS;
        if (speaking) {
            if (!piece)
                piece = { startMs: Math.max(0, t - frameMs - (preroll ? PREROLL_MS : 0)), chunks: preroll ? [preroll] : [], speechMs: 0, silenceMs: 0, lastSpeechMs: t };
            piece.chunks.push(frame);
            piece.speechMs += frameMs;
            piece.silenceMs = 0;
            piece.lastSpeechMs = t;
        }
        else if (piece) {
            piece.chunks.push(frame);
            piece.silenceMs += frameMs;
            if (piece.silenceMs >= END_OF_PIECE_MS)
                endPiece();
        }
        else {
            preroll = frame;
            if (t - lastActivity >= HEARTBEAT_MS) { // one quiet second so the backend can offer a nudge
                enqueue(Math.max(0, t - 1000), t, [new Float32Array(Math.round(ctx.sampleRate))]);
                lastActivity = t;
            }
        }
        if (piece && t - piece.startMs >= MAX_PIECE_MS)
            endPiece();
    };

    return {
        /** Milliseconds since the lesson began, not counting pauses. */
        now,
        nextSeq: () => seq,
        pause() {
            if (pausedAt === null) {
                endPiece();
                pausedAt = performance.now();
            }
        },
        resume() {
            if (pausedAt !== null) {
                pausedTotal += performance.now() - pausedAt;
                pausedAt = null;
                lastActivity = now();
            }
        },
        /** Send what has been said so far and wait (up to 20 s) until the backend has answered everything. */
        async flush() {
            endPiece();
            const until = performance.now() + 20000;
            while ((queue.length || sending) && performance.now() < until)
                await new Promise(r => setTimeout(r, 150));
            return !queue.length;
        },
        stop() {
            stopped = true;
            processor.onaudioprocess = null;
            try {
                source.disconnect();
                processor.disconnect();
                mute.disconnect();
                ctx.close();
            }
            catch { /* already closed */ }
        },
    };
}
