import { useEffect, useState } from 'react';
import { HashRouter, Route, Routes } from 'react-router-dom';
import * as api from './lib/api.js';
import { Context } from './context/AppContext.js';
import { Shell } from './components/Shell.jsx';
import { Login } from './pages/Login.jsx';
import { Dashboard } from './pages/Dashboard.jsx';
import { Schedule } from './pages/Schedule.jsx';
import { HistoryPage } from './pages/History.jsx';
import { PerformanceOverview } from './pages/Performance.jsx';
import { ReportPage } from './pages/Report.jsx';
import { Setup } from './pages/Setup.jsx';
import { DeviceCheck } from './pages/DeviceCheck.jsx';
import { Room } from './features/simulator/room/Room.jsx';
import { readStore, saveStore } from './lib/data.js';

export function App() {
    const [user, setUser] = useState(api.getUser);
    const [store, setStore] = useState(() => readStore(api.getUser()));
    const [storageError, setStorageError] = useState(false);
    useEffect(() => {
        if (!user) return;
        try {
            saveStore(store, user);
            setStorageError(false);
        } catch {
            setStorageError(true);
        }
    }, [store, user]);
    if (!user)
        return (
            <Login
                onLogin={(next) => {
                    // The router keeps whatever page the address bar still shows from before logging out (or from a
                    // link opened while signed out). Signing in always starts at the Dashboard.
                    window.location.hash = '#/';
                    setStore(readStore(next));
                    setUser(next);
                }}
            />
        );
    return (
        <Context.Provider
            value={{
                store,
                setStore,
                user,
                logout: () => {
                    api.logout();
                    setUser(null);
                },
            }}
        >
            <HashRouter>
                {storageError && (
                    <div className="storage-error" role="alert">
                        {'Penyimpanan peramban penuh atau tidak tersedia. Perubahan belum tersimpan. '}
                        <button
                            onClick={() => {
                                try {
                                    saveStore(store, user);
                                    setStorageError(false);
                                } catch {
                                    setStorageError(true);
                                }
                            }}
                        >
                            Coba simpan lagi
                        </button>
                    </div>
                )}
                <Shell>
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/schedule" element={<Schedule />} />
                        <Route path="/history" element={<HistoryPage />} />
                        <Route path="/performance" element={<PerformanceOverview />} />
                        <Route path="/report/:id" element={<ReportPage />} />
                        <Route path="/simulator/setup" element={<Setup />} />
                        <Route path="/simulator/check" element={<DeviceCheck />} />
                        <Route path="/simulator/room" element={<Room />} />
                        <Route path="*" element={<Dashboard />} />
                    </Routes>
                </Shell>
            </HashRouter>
        </Context.Provider>
    );
}
