import { useEffect, useRef } from 'react';

export function useDialogFocus(open, onClose) {
    const close = useRef(onClose);
    close.current = onClose;
    useEffect(() => {
        if (!open) return;
        const previous = document.activeElement;
        const dialog = document.querySelector('[role="dialog"],[role="alertdialog"]');
        if (!dialog) return;
        const items = () =>
            Array.from(dialog.querySelectorAll('button:not([disabled]),a[href],input,select,textarea,[tabindex="0"]'));
        items()[0]?.focus();
        const handler = (e) => {
            if (e.key === 'Escape' && close.current) {
                e.preventDefault();
                close.current();
            }
            if (e.key === 'Tab') {
                const list = items(),
                    first = list[0],
                    last = list[list.length - 1];
                if (e.shiftKey && document.activeElement === first) {
                    e.preventDefault();
                    last?.focus();
                } else if (!e.shiftKey && document.activeElement === last) {
                    e.preventDefault();
                    first?.focus();
                }
            }
        };
        const old = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        const main = document.getElementById('main-content');
        if (dialog.classList.contains('sidebar') && main) main.inert = true;
        document.addEventListener('keydown', handler);
        return () => {
            document.body.style.overflow = old;
            if (main) main.inert = false;
            document.removeEventListener('keydown', handler);
            previous?.focus();
        };
    }, [open]);
}
