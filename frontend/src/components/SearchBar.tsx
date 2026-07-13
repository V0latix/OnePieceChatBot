"use client";

import { useCallback, useRef, useState } from "react";
import { searchChunks, SearchResult } from "../lib/api";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Input } from "./ui/input";

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await searchChunks(q.trim());
      setResults(data);
    } catch {
      setError("Erreur lors de la recherche.");
      setResults(null);
    } finally {
      setLoading(false);
    }
  }, []);

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
    <Card className="fade-in">
      <CardHeader>
        <CardTitle>Recherche</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            type="search"
            value={query}
            onChange={handleChange}
            placeholder="Recherche directe dans les chunks…"
            className="flex-1"
          />
          <Button type="submit" variant="secondary" size="sm" disabled={loading || !query.trim()}>
            {loading ? "…" : "Go"}
          </Button>
        </form>

        {error && <p className="text-xs text-destructive">{error}</p>}

        {results && results.length === 0 && <p className="text-xs text-muted-foreground">Aucun resultat.</p>}

        {results && results.length > 0 && (
          <ul className="flex max-h-72 flex-col gap-2 overflow-y-auto">
            {results.map((r) => (
              <li key={r.chunk_id} className="border border-foreground bg-background p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold uppercase">{r.entity_name}</span>
                  <span className="shrink-0 text-[10px] text-muted-foreground">{r.section}</span>
                </div>
                <p className="mt-1 line-clamp-3 text-xs">{r.content}</p>
                <div className="mt-2 flex items-center gap-3">
                  <span className="text-[10px] text-muted-foreground">score {r.score.toFixed(3)}</span>
                  {r.source_url && (
                    <a
                      href={r.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] font-bold text-primary underline underline-offset-2 hover:text-primary-hover"
                    >
                      source ↗
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
