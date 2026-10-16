// The two demo teachers on the login screen. Bu Rina has practised before (her history is filled in); Bu Lina is new.
export const PERSONAS = [
    { name: 'Bu Rina', note: 'Sudah pernah berlatih', returning: true },
    { name: 'Bu Lina', note: 'Pengguna baru', returning: false },
];
export const isReturning = (user) => PERSONAS.find((p) => p.name === user?.name)?.returning ?? true;
