import { EntityRelation } from "../lib/api";

interface RelationsListProps {
  relations: EntityRelation[];
}

export default function RelationsList({ relations }: RelationsListProps) {
  if (!relations.length) {
    return <p className="text-sm text-muted-foreground">Aucune relation graphe disponible.</p>;
  }

  return (
    <ul className="space-y-2 text-sm">
      {relations.slice(0, 15).map((row, index) => (
        <li
          key={`${row.source}-${row.relation}-${row.target}-${index}`}
          className="border border-foreground bg-background px-3 py-2"
        >
          <span className="font-bold text-primary">{row.source ?? "?"}</span> -[{row.relation ?? "?"}]-&gt;{" "}
          {row.target ?? "?"}
        </li>
      ))}
    </ul>
  );
}
