import { useState } from 'react';
import * as api from '../lib/api.js';
import { APP_NAME } from '../lib/config.js';
import { PERSONAS } from '../lib/personas.js';

export function Login({ onLogin }) {
    const [name, setName] = useState(''); // nobody is chosen for the teacher
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);
    async function submit(e) {
        e.preventDefault();
        if (busy || !name) return;
        setBusy(true);
        setError('');
        try {
            onLogin(await api.login(name));
        } catch (err) {
            setError(err.message);
            setBusy(false);
        }
    }
    return (
        <main className="login-page">
            <div className="login-brand">
                <img src="./assets/logo.svg" alt={APP_NAME} />
                <p>
                    Listen. Ask. Suggest.
                </p>
            </div>
            <form className="login-card" onSubmit={submit}>
                <h1>Login</h1>
                <p className="muted">Pilih akun</p>
                <fieldset className="persona-toggle">
                    <legend className="sr-only">Akun</legend>
                    {PERSONAS.map((p) => (
                        <label className="persona" key={p.name}>
                            <input
                                type="radio"
                                name="persona"
                                value={p.name}
                                checked={name === p.name}
                                onChange={() => setName(p.name)}
                            />
                            <strong>{p.name}</strong>
                            <small>{p.note}</small>
                        </label>
                    ))}
                </fieldset>
                {error && (
                    <span className="error-text" role="alert">
                        {error}
                    </span>
                )}
                <button className="button button-primary" type="submit" disabled={busy || !name}>
                    {busy ? 'Masuk...' : 'Login'}
                </button>
            </form>
        </main>
    );
}
