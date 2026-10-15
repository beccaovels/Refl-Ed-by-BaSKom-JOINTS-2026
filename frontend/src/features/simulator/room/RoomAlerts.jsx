import { Link } from 'react-router-dom';
import { WifiOff } from 'lucide-react';

export function RoomAlerts({
    setupError,
    sendProblem,
    offline,
    onRetryOnline,
    deviceError,
    onCloseDeviceError,
    storageError,
}) {
    return (
        <>
            {(setupError || sendProblem) && (
                <div className="room-alert" role="alert">
                    {setupError || `Audio belum terkirim: ${sendProblem} Mencoba lagi...`}
                </div>
            )}
            {offline && (
                <div className="room-alert" role="alert">
                    <WifiOff size={17} />
                    {'Koneksi terputus. Sesi dijeda; catatan lokal tetap ada. '}
                    <button onClick={() => onRetryOnline()}>Coba sambungkan</button>
                </div>
            )}
            {deviceError && (
                <div className="room-alert" role="alert">
                    {deviceError}
                    <Link to="/simulator/check">Periksa perangkat</Link>
                    <button onClick={() => onCloseDeviceError()}>Tutup</button>
                </div>
            )}
            {storageError && (
                <div className="room-alert" role="alert">
                    Penyimpanan lokal gagal. Jangan tutup halaman sebelum sesi berhasil disimpan.
                </div>
            )}
        </>
    );
}
