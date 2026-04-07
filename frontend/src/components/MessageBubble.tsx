import { SourceCitation as SourceCitationType } from "../lib/api";
import SourceCitation from "./SourceCitation";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitationType[];
  confidence?: number;
}

export default function MessageBubble({ role, content, sources = [], confidence }: MessageBubbleProps) {
  return (
    <article
      className={`rounded-xl border px-4 py-3 text-sm leading-relaxed ${
        role === "user"
          ? "ml-auto max-w-[88%] border-ember bg-[#2b1f1a]"
          : "mr-auto max-w-[88%] border-gold/40 bg-[#131f33]"
      }`}
    >
      <p>{content}</p>
      {role === "assistant" && sources.length > 0 ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {sources.map((source) => (
            <SourceCitation key={`${source.entity_name}-${source.section}-${source.source_url}`} source={source} />
          ))}
          {typeof confidence === "number" ? (
            <span className="text-[11px] text-[#bfae8d]">Confiance: {(confidence * 100).toFixed(0)}%</span>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
