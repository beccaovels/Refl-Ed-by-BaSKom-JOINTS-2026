import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../../../lib/api.js';
import { useApp } from '../../../context/AppContext.js';
import { useDialogFocus } from '../../../hooks/useDialogFocus.js';
import { current, readDraft } from '../../../lib/lesson.js';
import { device } from '../../../lib/device.js';
import { saveStore } from '../../../lib/data.js';
import { startRecorder } from '../audio/recorder.js';
import { adaptReport } from '../../../lib/adapt.js';
import { REFL_NAME } from '../../../lib/config.js';
import { ReflPopup } from './ReflPopup.jsx';
import { playReflChime } from './reflSound.js';
import { LessonStage } from './LessonStage.jsx';
import { RoomAlerts } from './RoomAlerts.jsx';
import { RoomControls } from './RoomControls.jsx';
import { CapstoneDialog, SavingDialog, SaveErrorDialog } from './RoomDialogs.jsx';
import { RoomHeader } from './RoomHeader.jsx';

export function Room() {
    const navigate = useNavigate();
    const { store, setStore, user } = useApp();
    const [draft] = useState(readDraft);
    const [config] = useState(() => draft?.config ?? current());
    const [id] = useState(() => draft?.id ?? crypto.randomUUID());
    const [saveError, setSaveError] = useState('');
    const [phase, setPhase] = useState(draft?.phase === 'loading' ? 'error' : (draft?.phase ?? 'live'));
    const [seconds, setSeconds] = useState(draft?.seconds ?? 0);
    const [paused, setPaused] = useState(Boolean(draft));
    const [camera, setCamera] = useState(Boolean(device.stream?.getVideoTracks().some((t) => t.readyState === 'live')));
    const [micOn, setMicOn] = useState(true);
    const [questionCount, setQuestionCount] = useState(draft?.questionCount ?? 0);
    const [moments, setMoments] = useState(draft?.moments ?? []);
    const [answer, setAnswer] = useState(draft?.answer ?? '');
    const [offline, setOffline] = useState(!navigator.onLine);
    const [deviceError, setDeviceError] = useState('');
    const [storageError, setStorageError] = useState(false);
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
    const [stageState, setStageState] = useState(draft?.stage ?? null);
    const [files, setFiles] = useState(config.files ?? []);
    const slideQueue = useRef([]);
    const signals = useRef(null); // the voice meter (vision/); its ten-second bins feed the Suara & ekspresi card
    const binQueue = useRef([]);
    const binSending = useRef(false);
    const slideSending = useRef(false);
    const sessionRef = useRef(null);
    sessionRef.current = sessionId;
    const shareRef = useRef(null);
    const [shareStream, setShareStream] = useState(null);
    const sharing = Boolean(shareStream);
    const canShare = Boolean(navigator.mediaDevices?.getDisplayMedia);
    const timer = useRef();
    const liveAt = () =>
        `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
    useDialogFocus(phase === 'capstone' || phase === 'error');
    useEffect(() => {
        if (!device.stream?.getAudioTracks().some((t) => t.readyState === 'live')) {
            navigate('/simulator/check', {
                replace: true,
            });
            return;
        }
        const track = device.stream.getAudioTracks()[0];
        const ended = () => {
            setPaused(true);
            setMicOn(false);
            setDeviceError('Mikrofon terputus. Periksa kembali perangkat untuk melanjutkan; catatan tetap tersimpan.');
        };
        track.addEventListener('ended', ended);
        return () => {
            track.removeEventListener('ended', ended);
            if (timer.current) clearTimeout(timer.current);
        };
    }, [navigate]);
    useEffect(() => {
        if (video.current && device.stream) video.current.srcObject = device.stream;
    }, [camera]);
    // Make the session on the backend once, then listen to the microphone and send numbered pieces of speech.
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                if (!sessionId && !starting.current) {
                    starting.current = (async () => {
                        const list = await api.profiles();
                        // Never another subject's profile: its student would ask about the wrong subject.
                        const profile = list.find((p) => p.subject === config.lesson.subject);
                        if (!profile)
                            throw new Error(
                                `Belum ada profil untuk mata pelajaran ${config.lesson.subject} di server. Isi SHOW_UNTESTED_PROFILES=true di backend/.env, atau pilih mata pelajaran yang sudah punya profil.`,
                            );
                        const body = {
                            profile_id: profile.id,
                            class_name: config.lesson.kelas,
                            subject: config.lesson.subject,
                            chapter: config.lesson.chapter,
                            sub_chapter: config.lesson.subchapter,
                            material_id: config.materialId ?? null,
                            camera_on: Boolean(device.stream?.getVideoTracks().length),
                            demo_mode: true,
                        };
                        let created;
                        try {
                            created = await api.createSession(body);
                        } catch (err) {
                            // The material is optional. One that no longer exists (or is not this teacher's) must not
                            // stop the lesson from being created, or it could never be ended or reach the history.
                            if (!(err instanceof api.ApiError && err.status === 404 && body.material_id)) throw err;
                            created = await api.createSession({ ...body, material_id: null });
                            setFiles([]);
                        }
                        if (config.scheduleId)
                            // started: no longer "terlewat" when its time passes, even if the lesson is still going on
                            setStore((prev) => ({
                                ...prev,
                                schedules: prev.schedules.map((x) =>
                                    x.id === config.scheduleId && x.status === 'scheduled'
                                        ? { ...x, sessionId: created.id }
                                        : x,
                                ),
                            }));
                        return created.id;
                    })();
                }
                const sid = sessionId ?? (await starting.current);
                if (cancelled || !device.stream) return;
                setSessionId(sid);
                recorder.current = startRecorder(device.stream, {
                    sessionId: sid,
                    startSeq: draft?.nextSeq ?? 0,
                    offsetMs: (draft?.seconds ?? 0) * 1000,
                    onReply: handleReply,
                    onProblem: (m) => setSendProblem(m ?? ''),
                });
                setRecorderReady(true);
                startSignals(sid);
            } catch (err) {
                starting.current = null;
                if (!cancelled) setSetupError(err.message);
            }
        })();
        return () => {
            cancelled = true;
            signals.current?.stop();
            signals.current = null;
            recorder.current?.stop();
            recorder.current = null;
            setRecorderReady(false);
        };
    }, []);
    useEffect(() => {
        if (paused || offline) recorder.current?.pause();
        else recorder.current?.resume();
    }, [paused, offline, recorderReady]);
    // Every page turn is logged with the lesson clock (the same one the audio uses). A turn is kept until the backend
    // has it; sending it twice is harmless because the backend ignores a repeat.
    // Voice signals run in the browser (loudness and pitch, nothing recorded); only these small bins are sent.
    // The camera is left off here: bins then carry voice only, which the report scores on its own.
    async function startSignals(sid) {
        try {
            const { startSignals: start } = await import('../vision/index.ts'); // loaded only when a lesson starts
            if (signals.current || !device.stream || !recorder.current) return;
            signals.current = await start({
                stream: device.stream,
                now: () => recorder.current?.now() ?? 0,
                onBin: (bin) => {
                    binQueue.current.push(bin);
                    flushBins(sid);
                },
            });
        } catch (err) {
            console.warn('Voice signals are off; the report goes on without Suara & ekspresi.', err);
        }
    }
    async function flushBins(sid = sessionRef.current) {
        if (binSending.current || !sid) return;
        binSending.current = true;
        try {
            while (binQueue.current.length) {
                const batch = binQueue.current.slice(0, 60);
                try {
                    await api.sendSignals(sid, batch);
                } catch (err) {
                    if (!(err instanceof api.ApiError) || err.status === 0 || err.status >= 500) break; // try again later
                }
                binQueue.current.splice(0, batch.length); // sent, or refused for good
            }
        } finally {
            binSending.current = false;
        }
    }
    async function flushSlides() {
        if (slideSending.current || !sessionRef.current) return;
        slideSending.current = true;
        try {
            while (slideQueue.current.length) {
                const turn = slideQueue.current[0];
                try {
                    await api.sendSlide(sessionRef.current, turn.page, turn.t_ms);
                } catch (err) {
                    if (!(err instanceof api.ApiError) || err.status === 0 || err.status >= 500) break; // try again on the next tick
                }
                slideQueue.current.shift(); // sent, or refused for good (for example the lesson has ended)
            }
        } finally {
            slideSending.current = false;
        }
    }
    // `page` 0 means no slide text is on screen (a shared screen); the PDF page again when the teacher comes back.
    const lastLogged = useRef(null);
    function logStage(shown) {
        if (shown === lastLogged.current) return; // the same page again is not a page turn
        lastLogged.current = shown;
        slideQueue.current.push({
            page: shown,
            t_ms: Math.round(recorder.current?.now() ?? seconds * 1000),
        });
        flushSlides();
    }
    // The lesson's items, fresh from the server: a picture may have finished being read since Setup.
    const stillReading = files.some((f) => f.status === 'reading');
    useEffect(() => {
        if (!config.materialId) return;
        const load = () =>
            api
                .listMaterialFiles(config.materialId)
                .then((listed) => setFiles(listed.files))
                .catch(() => {});
        load();
        if (!stillReading) return;
        const timer = window.setInterval(load, 3000);
        return () => clearInterval(timer);
    }, [stillReading]);
    // Screen sharing stays in the browser: the picture is shown on the stage and never uploaded.
    async function startShare() {
        if (shareRef.current) return;
        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({
                video: {
                    frameRate: {
                        ideal: 15,
                        max: 15,
                    },
                    width: {
                        max: 1280,
                    },
                },
                audio: false,
                selfBrowserSurface: 'exclude',
            });
            shareRef.current = stream;
            stream.getVideoTracks()[0]?.addEventListener('ended', stopShare); // the browser's own "stop sharing"
            setShareStream(stream);
            if (config.materialId) logStage(0);
        } catch (err) {
            if (err?.name !== 'NotAllowedError' && err?.name !== 'AbortError')
                // closing the picker is not an error
                setDeviceError('Berbagi layar tidak bisa dimulai. Anda tetap bisa memakai materi.');
        }
    }
    function stopShare() {
        const stream = shareRef.current;
        if (!stream) return;
        shareRef.current = null;
        stream.getTracks().forEach((t) => t.stop());
        setShareStream(null);
    }
    useEffect(() => () => shareRef.current?.getTracks().forEach((t) => t.stop()), []);
    useEffect(() => {
        const timer = window.setInterval(() => {
            flushSlides();
            flushBins();
        }, 3000);
        flushSlides();
        return () => clearInterval(timer);
    }, [sessionId]);
    function handleReply(reply) {
        if (seen.current.has(reply.seq)) return;
        seen.current.add(reply.seq);
        const mmss = (ms) =>
            `${String(Math.floor(ms / 60000)).padStart(2, '0')}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}`;
        const added = [];
        if (reply.segment)
            added.push({
                at: mmss(reply.segment.start_ms),
                speaker: 'Guru',
                text: reply.segment.text,
                spoken: true, // kept for the report's transcript; not shown in the chat
            });
        if (reply.event) {
            added.push({
                at: mmss(reply.event.asked_at_ms),
                speaker: REFL_NAME,
                text: reply.event.text,
                id: reply.event.id,
                kind: reply.event.kind,
                satisfied: reply.event.satisfied ?? null,
            });
            if (reply.event.kind !== 'nudge') setQuestionCount((x) => x + 1);
        }
        if (added.length) setMoments((prev) => [...prev, ...added]);
    }
    useEffect(() => {
        const interval = window.setInterval(() => {
            if (phase === 'live' && !paused && !offline) setSeconds((s) => s + 1);
        }, 1000);
        return () => clearInterval(interval);
    }, [phase, paused, offline, deviceError]);
    useEffect(() => {
        const on = () => setOffline(false),
            off = () => setOffline(true);
        window.addEventListener('online', on);
        window.addEventListener('offline', off);
        return () => {
            window.removeEventListener('online', on);
            window.removeEventListener('offline', off);
        };
    }, []);
    useEffect(() => {
        try {
            localStorage.setItem(
                'gema-draft',
                JSON.stringify({
                    id,
                    config,
                    seconds,
                    moments,
                    answer,
                    phase,
                    questionCount,
                    sessionId,
                    capstone,
                    nextSeq: recorder.current?.nextSeq() ?? draft?.nextSeq ?? 0,
                    stage: stageState,
                }),
            );
            setStorageError(false);
        } catch {
            setStorageError(true);
        }
    }, [id, config, seconds, moments, answer, phase, questionCount]);
    function toggleMic() {
        const next = !micOn;
        device.stream?.getAudioTracks().forEach((t) => (t.enabled = next));
        setMicOn(next);
    }
    async function toggleCamera() {
        if (camera) {
            device.stream?.getVideoTracks().forEach((t) => {
                t.stop();
                device.stream?.removeTrack(t);
            });
            setCamera(false);
        } else
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: true,
                });
                stream.getVideoTracks().forEach((t) => device.stream?.addTrack(t));
                setCamera(true);
            } catch {
                setDeviceError('Kamera tidak tersedia. Latihan audio tetap bisa dilanjutkan.');
            }
    }
    useEffect(() => {
        if (phase === 'capstone') playReflChime();
    }, [phase]);
    async function endLesson() {
        if (phase !== 'live' || busy.current) return;
        if (!sessionId) {
            setDeviceError(setupError || 'Sesi belum tersambung ke server. Tunggu sebentar lalu coba lagi.');
            return;
        }
        busy.current = true;
        try {
            await recorder.current?.flush();
            const event = await api.endLesson(sessionId);
            setCapstone(event.text);
            setMoments((prev) => [
                ...prev,
                {
                    at: liveAt(),
                    speaker: REFL_NAME,
                    text: event.text,
                    id: event.id,
                    kind: 'capstone',
                },
            ]);
            setPhase('capstone');
        } catch (err) {
            setDeviceError(`Belum bisa mengakhiri sesi: ${err.message}`);
        } finally {
            busy.current = false;
        }
    }
    async function finish() {
        if (busy.current) return;
        busy.current = true;
        setPhase('loading');
        setSaveError('');
        try {
            await recorder.current?.flush();
            // Everything said is sent. Stop listening now: the lesson is over, and a piece cut while the report is
            // being made would only be refused by the backend (the session is closed) and retried for nothing.
            recorder.current?.stop();
            recorder.current = null;
            signals.current?.stop(); // emits the last, partly filled bin
            signals.current = null;
            for (let i = 0; i < 5 && binQueue.current.length; i++) {
                await flushBins(sessionId);
                if (binQueue.current.length) await new Promise((r) => setTimeout(r, 400));
            }
            const report = await api.waitForReport(sessionId);
            const all = [
                ...moments,
                ...(answer.trim()
                    ? [
                          {
                              at: liveAt(),
                              speaker: 'Guru',
                              text: answer.trim(),
                          },
                      ]
                    : []),
            ];
            const r = adaptReport(report, {
                id,
                lesson: config.lesson,
                material: config.material,
                camera,
                seconds,
                moments: all,
            });
            const next = {
                ...store,
                reports: [r, ...store.reports.filter((x) => x.id !== id)],
                schedules: store.schedules.map((s) =>
                    s.id === config.scheduleId
                        ? {
                              ...s,
                              status: 'done',
                          }
                        : s,
                ),
            };
            saveStore(next, user);
            setStore(next);
            localStorage.removeItem('gema-draft');
            recorder.current?.stop();
            recorder.current = null;
            shareRef.current?.getTracks().forEach((t) => t.stop());
            shareRef.current = null;
            device.stream?.getTracks().forEach((t) => t.stop());
            device.stream = null;
            navigate(`/report/${id}`);
        } catch (err) {
            // the server's own words (for example that the AI service was busy), not a generic message
            setSaveError(err instanceof api.ApiError ? err.message : '');
            setPhase('error');
        } finally {
            busy.current = false;
        }
    }
    return (
        <div className="room-page">
            <RoomHeader lesson={config.lesson} phase={phase} paused={paused} time={liveAt()} />
            <RoomAlerts
                setupError={setupError}
                sendProblem={sendProblem}
                offline={offline}
                onRetryOnline={() => setOffline(!navigator.onLine)}
                deviceError={deviceError}
                onCloseDeviceError={() => setDeviceError('')}
                storageError={storageError}
            />
            <div className="room-grid">
                <LessonStage
                    lesson={config.lesson}
                    hasMaterial={Boolean(config.materialId)}
                    files={files}
                    sharing={sharing}
                    shareStream={shareStream}
                    canShare={canShare}
                    onStartShare={startShare}
                    onStopShare={stopShare}
                    onStage={logStage}
                    stageState={stageState}
                    onStageStateChange={setStageState}
                    paused={paused}
                    offline={offline}
                    camera={camera}
                    videoRef={video}
                />
            </div>
            <ReflPopup
                moments={moments}
                live={phase === 'live'}
                paused={paused}
                onAddNote={(text) => setMoments((m) => [...m, { at: liveAt(), speaker: 'Guru', text }])}
            />
            <RoomControls
                micOn={micOn}
                onToggleMic={toggleMic}
                camera={camera}
                onToggleCamera={toggleCamera}
                canShare={canShare}
                sharing={sharing}
                onStartShare={startShare}
                onStopShare={stopShare}
                paused={paused}
                onTogglePause={() => setPaused(!paused)}
                phase={phase}
                offline={offline}
                onEnd={endLesson}
            />
            {phase === 'capstone' && (
                <CapstoneDialog
                    question={capstone}
                    pose={(moments.length % 2) + 1}
                    answer={answer}
                    onAnswer={setAnswer}
                    onFinish={finish}
                />
            )}
            {phase === 'loading' && <SavingDialog />}
            {phase === 'error' && <SaveErrorDialog onRetry={finish} reason={saveError} />}
        </div>
    );
}
