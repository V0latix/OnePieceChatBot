import { SourceCitation as SourceCitationType } from "../lib/api";

interface SourceCitationProps {
  source: SourceCitationType;
}

export default function SourceCitation({ source }: SourceCitationProps) {
  const href = source.source_url?.trim();
  const label = `${source.entity_name} · ${source.section}`;

  if (!href) {
    return (
      <span className="rounded-full border border-gold/20 bg-[#122742] px-2 py-1 text-[11px] text-[#d7c9aa]" title={label}>
        {label}
      </span>
    );
  }

  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="rounded-full border border-gold/25 bg-[#122742] px-2 py-1 text-[11px] text-[#e8d7b3] transition hover:border-gold hover:text-[#fff2cf]"
      title={label}
    >
      {label}
    </a>
  );
}
