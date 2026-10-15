export function PageHeading({ title, description, action }) {
    return (
        <div className="page-heading">
            <div>
                <h1>{title}</h1>
                <p className="page-subtitle">{description}</p>
            </div>
            {action}
        </div>
    );
}
