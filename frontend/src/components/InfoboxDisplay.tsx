interface InfoboxDisplayProps {
  infobox: Record<string, string>;
}

function formatLabel(raw: string): string {
  return raw
    .replace(/_/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

export default function InfoboxDisplay({ infobox }: InfoboxDisplayProps) {
  const entries = Object.entries(infobox).slice(0, 12);

  if (entries.length === 0) {
    return <p className="text-sm text-[#bba884]">Aucune donnee d'infobox disponible.</p>;
  }

  return (
    <dl className="grid gap-2 sm:grid-cols-2">
      {entries.map(([key, value]) => (
        <div key={key} className="rounded-lg border border-gold/15 bg-[#0f1b30] px-3 py-2">
          <dt className="text-[11px] uppercase tracking-[0.14em] text-gold">{formatLabel(key)}</dt>
          <dd className="mt-1 text-sm text-[#e2d2b0]">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
