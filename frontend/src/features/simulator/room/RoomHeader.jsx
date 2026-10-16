import { Radio, Clock3 } from 'lucide-react';

export function RoomHeader({ lesson, phase, paused, time }) {
    return (
        <div className="room-header">
            <div>
                <div>
                    <strong>Ruang latihan</strong>
                    <small>
                        {lesson.subject}
                        {' · '}
                        {lesson.chapter}
                        {' · '}
                        {lesson.kelas}
                    </small>
                </div>
            </div>
            <div className="room-meta">
                <span className="room-timer">
                    <Clock3 size={18} />
                    {time}
                </span>
                <span className={`room-state ${phase === 'live' && paused ? 'is-paused' : ''}`} role="status">
                    <Radio size={15} />
                    {phase === 'live'
                        ? paused
                            ? 'Dijeda'
                            : 'Sesi berlangsung'
                        : phase === 'capstone'
                          ? 'Pertanyaan akhir'
                          : 'Memproses'}
                </span>
            </div>
        </div>
    );
}
