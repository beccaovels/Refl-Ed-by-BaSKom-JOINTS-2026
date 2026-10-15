// Words that explain a finished report in the latest-report cards (Dashboard, Performa).
//
// The backend writes a short summary for every report it makes (`overall.summary`), grounded in that lesson's own
// quotes; that is used whenever there is one. Reports without it (made before it was kept, or the built-in examples)
// get a sentence built only from the scores they hold. Nothing is invented: every name and number comes from the report.
const list = (items) => (items.length < 2 ? (items[0] ?? '') : `${items.slice(0, -1).join(', ')} dan ${items.at(-1)}`);
const mark = (d) => `${d.name} (${d.score})`;

export function describeReport(r) {
    if (r.summary) return r.summary;
    if (r.overall === null || r.overall === undefined) return 'Sesi ini terlalu singkat untuk diberi skor.';
    const scored = (r.dimensions ?? []).filter((d) => typeof d.score === 'number');
    if (!scored.length) return null;
    const high = Math.max(...scored.map((d) => d.score));
    const low = Math.min(...scored.map((d) => d.score));
    const best = scored.filter((d) => d.score === high).slice(0, 2);
    const sentences = [`Yang paling menonjol: ${list(best.map(mark))}.`];
    if (low < high) sentences.push(`Yang bisa dilatih lagi: ${mark(scored.find((d) => d.score === low))}.`);
    return sentences.join(' ');
}
