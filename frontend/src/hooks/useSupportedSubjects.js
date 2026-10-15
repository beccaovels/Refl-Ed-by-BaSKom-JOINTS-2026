import { useEffect, useState } from 'react';
import { profiles } from '../lib/api.js';

// Which subjects the backend has a profile for (docs/api-contract.md, GET /profiles). A lesson in any other subject
// would be asked by a student written for a different subject, so Setup only offers these. Fetched once per visit.
let known = null; // a Set of subject names, once the backend has answered
let asking = null;

export function useSupportedSubjects() {
    const [subjects, setSubjects] = useState(known);
    useEffect(() => {
        if (known) return;
        let gone = false;
        asking ??= profiles()
            .then((list) => (known = new Set(list.map((p) => p.subject))))
            .catch(() => null) // unreachable: offer everything, the Room will say what is wrong
            .finally(() => {
                asking = null;
            });
        asking.then((result) => !gone && setSubjects(result));
        return () => {
            gone = true;
        };
    }, []);
    return subjects; // null until known
}
