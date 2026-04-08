"use client";

import { useCallback, useRef, useState } from "react";
import { searchChunks, SearchResult } from "../lib/api";

interface SearchBarProps {
  spoilerLimitArc?: string;
}

export default function SearchBar({ spoilerLimitArc }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSearch = useCallback(
    async (q: string) => {
      if (!q.trim()) {
        setResults(null);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const data = await searchChunks(q.trim(), undefined, spoilerLimitArc);
        setResults(data);
      } catch {
        setError("Erreur lors de la recherche.");
        setResults(null);
      } finally {
        setLoading(false);
      }
    },
    [spoilerLimitArc],
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSearch(val), 400);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (debounceRef.current) clearTimeout(debounceRef.current);
    runSearch(query);
  };

  return (
    <div className="card fade-in flex flex-col gap-3 rounded-2xl p-4">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="search"
          value={query}
          onChange={handleChange}
          placeholder="Recherche directe dans les chunks…"
          className="flex-1 rounded-lg border border-gold/30 bg-[#0d1729] px-3 py-2 text-sm text-[#d9caa8] placeholder:text-[#6b6047] focus:outline-none focus:ring-1 focus:ring-gold/50"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="rounded-lg border border-gold/30 bg-[#0d1729] px-3 py-2 text-xs text-gold disabled:opacity-40"
        >
          {loading ? "…" : "Go"}
        </button>
      </form>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {results && results.length === 0 && (
        <p className="text-xs text-[#6b6047]">Aucun resultat.</p>
      )}

      {results && results.length > 0 && (
        <ul className="flex max-h-72 flex-col gap-2 overflow-y-auto">
          {results.map((r) => (
            <li key={r.chunk_id} className="rounded-lg border border-white/5 bg-[#0a1526] p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-gold">{r.entity_name}</span>
                <span className="shrink-0 text-[10px] text-[#6b6047]">{r.section}</span>
              </div>
              <p className="mt-1 line-clamp-3 text-xs text-[#c4b898]">{r.content}</p>
              <div className="mt-1 flex items-center gap-3">
                <span className="text-[10px] text-[#6b6047]">score {r.score.toFixed(3)}</span>
                {r.source_url && (
                  <a
                    href={r.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] text-gold/60 hover:text-gold"
                  >
                    source ↗
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
