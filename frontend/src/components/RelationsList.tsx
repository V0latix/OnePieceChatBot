import { EntityRelation } from "../lib/api";

interface RelationsListProps {
  relations: EntityRelation[];
}

export default function RelationsList({ relations }: RelationsListProps) {
  if (!relations.length) {
    return <p className="text-sm text-[#bba884]">Aucune relation graphe disponible.</p>;
  }

  return (
    <ul className="space-y-2 text-sm text-[#ddd0b3]">
      {relations.slice(0, 15).map((row, index) => (
        <li key={`${row.source}-${row.relation}-${row.target}-${index}`} className="rounded-lg border border-gold/15 bg-[#0f1b30] px-3 py-2">
          <span className="text-gold">{row.source ?? "?"}</span> -[{row.relation ?? "?"}]-&gt; {row.target ?? "?"}
        </li>
      ))}
    </ul>
  );
}
