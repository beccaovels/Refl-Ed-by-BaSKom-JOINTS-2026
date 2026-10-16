import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { CalendarDays, ChartNoAxesCombined, ChevronLeft, History, Home, Menu, X } from 'lucide-react';
import { useApp } from '../context/AppContext.js';
import { Reminder } from './Reminder.jsx';
import { useDialogFocus } from '../hooks/useDialogFocus.js';
import { device } from '../lib/device.js';
import { APP_NAME } from '../lib/config.js';

const nav = [
    {
        to: '/',
        label: 'Dashboard',
        icon: Home,
    },
    {
        to: '/schedule',
        label: 'Jadwal',
        icon: CalendarDays,
    },
    {
        to: '/history',
        label: 'Riwayat',
        icon: History,
    },
    {
        to: '/performance',
        label: 'Performa',
        icon: ChartNoAxesCombined,
    },
];

export function Shell({ children }) {
    const { user, logout } = useApp();
    const location = useLocation();
    const inRoom = location.pathname === '/simulator/room'; // the room draws its own header
    const inSimulator = location.pathname.startsWith('/simulator'); // and these pages need no breadcrumb
    const [open, setOpen] = useState(false);
    const [collapsed, setCollapsed] = useState(false);
    useDialogFocus(open, () => setOpen(false));
    useEffect(() => {
        window.scrollTo(0, 0);
        setOpen(false);
        if (!['/simulator/check', '/simulator/room'].includes(location.pathname)) {
            device.stream?.getTracks().forEach((t) => t.stop());
            device.stream = null;
        }
    }, [location.pathname]);
    useEffect(() => {
        if (!open) return;
        const close = (e) => {
            if (e.key === 'Escape') setOpen(false);
        };
        window.addEventListener('keydown', close);
        return () => window.removeEventListener('keydown', close);
    }, [open]);
    return (
        <>
            <a className="skip-link" href="#main-content">
                Lewati ke konten
            </a>
            <div className={`app-shell ${collapsed ? 'nav-collapsed' : ''}`}>
                <button className="mobile-menu icon-button" onClick={() => setOpen(true)} aria-label="Buka navigasi">
                    <Menu size={22} />
                </button>
                {open && <button className="nav-scrim" aria-label="Tutup navigasi" onClick={() => setOpen(false)} />}
                <aside
                    role={open ? 'dialog' : undefined}
                    aria-modal={open ? true : undefined}
                    aria-label={`Menu ${APP_NAME}`}
                    className={`sidebar ${open ? 'open' : ''}`}
                >
                    <div className="brand">
                        <Link to="/" className="brand-logo" aria-label={`${APP_NAME}, ke Dashboard`}>
                            <img src="./assets/logo.svg" alt="" />
                        </Link>
                        <button
                            className="close-nav icon-button"
                            aria-label="Tutup navigasi"
                            onClick={() => setOpen(false)}
                        >
                            <X size={20} />
                        </button>
                    </div>
                    <nav aria-label="Navigasi utama">
                        {nav.map(({ to, label, icon: Icon }) => (
                            <NavLink
                                to={to}
                                end={to === '/'}
                                onClick={() => setOpen(false)}
                                className={({ isActive }) =>
                                    `nav-link ${isActive || (to === '/performance' && location.pathname.startsWith('/report/')) ? 'active' : ''}`
                                }
                                title={label}
                                aria-label={label}
                                key={to}
                            >
                                <Icon size={20} />
                                <span>{label}</span>
                            </NavLink>
                        ))}
                    </nav>
                    <div className="sidebar-bottom">
                        <button
                            className="collapse-button"
                            onClick={() => setCollapsed(!collapsed)}
                            aria-label={collapsed ? 'Perluas navigasi' : 'Ciutkan navigasi'}
                        >
                            <ChevronLeft size={18} className={collapsed ? 'rotated' : ''} />
                            <span>Ciutkan menu</span>
                        </button>
                    </div>
                </aside>
                <main className="main" id="main-content" tabIndex={-1}>
                    {!inRoom && (
                        <div className="topbar">
                            {!inSimulator && (
                                <span className="topbar-label">
                                    {`${APP_NAME} `}
                                    <span>/</span>
                                    {' Ruang latihan'}
                                </span>
                            )}
                            <div className="topbar-right">
                                <button
                                    className="text-link logout-link"
                                    onClick={logout}
                                >{`Keluar (${user.name})`}</button>
                                <span className="avatar" aria-label={`Masuk sebagai ${user.name}`} title={user.name}>
                                    {user.name.trim().split(/\s+/).pop()[0]?.toUpperCase() ?? 'G'}
                                </span>
                            </div>
                        </div>
                    )}
                    <Reminder />
                    {children}
                </main>
            </div>
        </>
    );
}
