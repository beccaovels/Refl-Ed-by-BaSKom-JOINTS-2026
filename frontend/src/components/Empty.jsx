import { image } from '../lib/data.js';

export function Empty({ title, body, art, action }) {
    return (
        <div className="empty-state">
            <img src={image(art)} alt="" />
            <div>
                <h3>{title}</h3>
                <p>{body}</p>
                {action}
            </div>
        </div>
    );
}
