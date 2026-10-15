import { Link } from 'react-router-dom';

export function Button({
    children,
    to,
    state,
    onClick,
    variant = 'primary',
    icon: Icon,
    type = 'button',
    disabled = false,
}) {
    const cls = `button button-${variant}`;
    return to ? (
        <Link className={cls} to={to} state={state}>
            {Icon && <Icon size={18} />}
            <span>{children}</span>
        </Link>
    ) : (
        <button className={cls} onClick={onClick} type={type} disabled={disabled}>
            {Icon && <Icon size={18} />}
            <span>{children}</span>
        </button>
    );
}
