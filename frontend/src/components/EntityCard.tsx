interface EntityCardProps {
  name: string;
  type: string;
  facts: string[];
}

export default function EntityCard({ name, type, facts }: EntityCardProps) {
  return (
    <aside className="card fade-in rounded-2xl p-5 md:p-6">
      <h3 className="text-2xl tracking-wide [font-family:var(--font-display)]">{name}</h3>
      <p className="mb-4 text-xs uppercase tracking-[0.2em] text-gold">{type}</p>
      <ul className="space-y-2 text-sm text-[#ddd0b3]">
        {facts.map((fact) => (
          <li key={fact} className="rounded-lg border border-gold/15 bg-[#0f1b30] px-3 py-2">
            {fact}
          </li>
        ))}
      </ul>
    </aside>
  );
}
