import { useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { ShieldCheck, ArrowRight } from 'lucide-react';
import MaterialUploader from '../features/setup/MaterialUploader.jsx';
import { Button } from '../components/Button.jsx';
import { PageHeading } from '../components/PageHeading.jsx';
import { LessonFields } from '../components/LessonFields.jsx';
import { current } from '../lib/lesson.js';
import { sameLesson, useLessons } from '../hooks/useLessons.js';
import { image, lessonFromParams } from '../lib/data.js';
import { APP_NAME } from '../lib/config.js';

export function Setup() {
    const [params] = useSearchParams();
    const navigate = useNavigate();
    const returning = useLocation().state?.resume === true; // came back from "Periksa perangkat" for this same lesson
    const [lesson, setLesson] = useState(() => (params.has('subject') ? lessonFromParams(params) : current().lesson));
    const offered = useLessons()?.some((l) => sameLesson(l, lesson)); // only a lesson a profile covers can start
    const [materials, setMaterials] = useState(() => ({
        materialId: returning ? (current().materialId ?? null) : null,
        files: returning ? (current().files ?? []) : [],
        busy: false,
    }));
    function next() {
        localStorage.removeItem('gema-draft');
        sessionStorage.setItem(
            'gema-current-lesson',
            JSON.stringify({
                lesson,
                scheduleId: params.get('scheduleId'),
                material: materials.files.length
                    ? materials.files.length === 1
                        ? materials.files[0].filename
                        : `${materials.files.length} materi`
                    : null,
                materialId: materials.files.length ? materials.materialId : null,
                files: materials.files,
            }),
        );
        navigate('/simulator/check');
    }
    return (
        <div className="page flow-page">
            <div className="flow-steps">
                <span className="active" aria-current="step">
                    <i aria-hidden>1</i>
                    <b>Persiapan</b>
                </span>
                <span>
                    <i aria-hidden>2</i>
                    <b>Perangkat</b>
                </span>
                <span>
                    <i aria-hidden>3</i>
                    <b>Ruang latihan</b>
                </span>
                <span>
                    <i aria-hidden>4</i>
                    <b>Refleksi</b>
                </span>
            </div>
            <PageHeading
                title="Apa yang ingin Anda latih?"
                description={`Tentukan konteks pelajaran agar pertanyaan Siswa ${APP_NAME} terasa relevan.`}
            />
            <div className="setup-layout">
                <section className="card setup-card">
                    <h2>Topik latihan</h2>
                    <p className="muted">Pilihan di bawah adalah bab yang sudah punya profil mata pelajaran.</p>
                    <LessonFields value={lesson} onChange={setLesson} />
                    <MaterialUploader value={materials} onChange={setMaterials} />
                    <div className="setup-footer">
                        <Button to="/" variant="subtle">
                            Kembali
                        </Button>
                        <Button onClick={next} disabled={materials.busy || !offered} icon={ArrowRight}>
                            Periksa perangkat
                        </Button>
                    </div>
                </section>
                <aside className="setup-aside">
                    <div className="setup-art">
                        <img
                            src={image('simulation/teacher-practicing-camera.png')}
                            alt="Guru berlatih mengajar di depan kamera"
                        />
                    </div>
                    <div className="tip-card">
                        <ShieldCheck size={23} />
                        <div>
                            <strong>Ruang aman untuk mencoba</strong>
                            <p>{`Satu Siswa ${APP_NAME} akan menampilkan pertanyaan contoh sesuai topik. Anda boleh mulai tanpa kamera.`}</p>
                        </div>
                    </div>
                </aside>
            </div>
        </div>
    );
}
