import { Mic, MicOff, Camera, CameraOff, ScreenShare, ScreenShareOff, Pause, Play, Square } from 'lucide-react';
import { device } from '../../../lib/device.js';

export function RoomControls({
    micOn,
    onToggleMic,
    camera,
    onToggleCamera,
    canShare,
    sharing,
    onStartShare,
    onStopShare,
    paused,
    onTogglePause,
    phase,
    offline,
    onEnd,
}) {
    return (
        <>
            <div className="room-controls">
                <div className="control-group">
                    <button
                        onClick={onToggleMic}
                        className={`control ${micOn ? '' : 'control-off'}`}
                        aria-label={micOn ? 'Matikan mikrofon' : 'Nyalakan mikrofon'}
                        aria-pressed={micOn}
                    >
                        {micOn ? <Mic size={20} /> : <MicOff size={20} />}
                        <span>
                            {'Mikrofon '}
                            {micOn ? 'aktif' : 'mati'}
                        </span>
                    </button>
                    <button
                        onClick={onToggleCamera}
                        className="control"
                        aria-label={camera ? 'Matikan kamera' : 'Nyalakan kamera'}
                        aria-pressed={camera}
                    >
                        {camera ? <Camera size={20} /> : <CameraOff size={20} />}
                        <span>
                            {'Kamera '}
                            {camera ? 'aktif' : 'mati'}
                        </span>
                    </button>
                    {canShare && (
                        <button
                            onClick={sharing ? onStopShare : onStartShare}
                            className={`control ${sharing ? 'control-on' : ''}`}
                            aria-pressed={sharing}
                            aria-label={sharing ? 'Berhenti berbagi layar' : 'Bagikan layar'}
                        >
                            {sharing ? <ScreenShareOff size={20} /> : <ScreenShare size={20} />}
                            <span>{sharing ? 'Berhenti berbagi' : 'Bagikan layar'}</span>
                        </button>
                    )}
                    <button
                        onClick={onTogglePause}
                        className="control"
                        disabled={
                            phase !== 'live' ||
                            offline ||
                            !device.stream?.getAudioTracks().some((t) => t.readyState === 'live')
                        }
                        aria-label={paused ? 'Lanjutkan sesi' : 'Jeda sesi'}
                    >
                        {paused ? <Play size={20} /> : <Pause size={20} />}
                        <span>{paused ? 'Lanjutkan' : 'Jeda'}</span>
                    </button>
                </div>
                <button className="end-button" onClick={onEnd} disabled={phase !== 'live'}>
                    <Square size={18} fill="currentColor" />
                    {' Selesai mengajar'}
                </button>
            </div>
        </>
    );
}
