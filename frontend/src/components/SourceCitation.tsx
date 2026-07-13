import { SourceCitation as SourceCitationType } from "../lib/api";
import { Badge } from "./ui/badge";

interface SourceCitationProps {
  source: SourceCitationType;
}

export default function SourceCitation({ source }: SourceCitationProps) {
  const href = source.source_url?.trim();
  const label = `${source.entity_name} · ${source.section}`;

  if (!href) {
    return (
      <Badge variant="muted" title={label}>
        {label}
      </Badge>
    );
  }

  return (
    <a href={href} target="_blank" rel="noreferrer" title={label}>
      <Badge className="hover:bg-primary hover:text-primary-foreground">{label}</Badge>
    </a>
  );
}
