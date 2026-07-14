"use client";

import { useEffect, useState } from "react";

import ChatInterface from "../components/ChatInterface";
import EntityCard from "../components/EntityCard";
import SearchBar from "../components/SearchBar";
import { EntityResponse, fetchEntity } from "../lib/api";

// Doit rester aligne sur la procedure de redemarrage du README.
const BACKEND_COMMANDS: { terminal: string; command: string }[] = [
  { terminal: "Terminal 1 — backend (depuis la racine du repo)", command: "source .venv/bin/activate" },
  { terminal: "", command: "PYTHONPATH=src uvicorn api.main:app --host 127.0.0.1 --port 8000" },
  {
    terminal: "Terminal 2 — tunnel ngrok",
    command: "ngrok http --url=overdistant-colloquial-leonora.ngrok-free.dev 8000",
  },
];

interface EntityFetch {
  name: string;
  entity: EntityResponse | null;
  error: string | null;
}

export default function HomePage() {
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  // Le resultat porte le nom demande : setState ne se fait que dans les callbacks
  // async, jamais dans le corps de l'effet (cf. react-hooks/set-state-in-effect).
  const [fetched, setFetched] = useState<EntityFetch | null>(null);

  useEffect(() => {
    if (!selectedEntity) return;

    let cancelled = false;
    const name = selectedEntity;

    fetchEntity(name)
      .then((payload) => {
        if (!cancelled) setFetched({ name, entity: payload, error: null });
      })
      .catch(() => {
        if (!cancelled) setFetched({ name, entity: null, error: "Impossible de charger la fiche entite." });
      });

    return () => {
      cancelled = true;
    };
  }, [selectedEntity]);

  const settled = fetched && fetched.name === selectedEntity ? fetched : null;
  const entity = settled?.entity ?? null;
  const error = settled?.error ?? null;
  const loading = selectedEntity !== null && settled === null;

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 md:px-8 md:py-10">
      <header className="fade-in border border-foreground bg-card p-6 md:p-8">
        <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">Grand Line Intelligence</p>
        <h1 className="mt-2 font-display text-5xl font-extrabold uppercase leading-none tracking-tighter md:text-7xl">
          One Piece RAG
        </h1>
        <p className="mt-4 max-w-3xl text-sm text-muted-foreground md:text-base">
          Pose n&apos;importe quelle question sur le canon One Piece. Les reponses sont justifiees par des sources wiki.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.7fr_1fr]">
        <ChatInterface onPrimaryEntityChange={setSelectedEntity} />
        <div className="flex flex-col gap-6">
          <SearchBar />
          <EntityCard entity={entity} loading={loading} error={error} />
        </div>
      </div>

      <footer className="border border-foreground bg-card p-4">
        <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
          Backend local — commandes a lancer
        </p>
        <div className="mt-3 flex flex-col gap-1">
          {BACKEND_COMMANDS.map(({ terminal, command }) => (
            <div key={command} className="flex flex-col gap-1">
              {terminal ? (
                <p className="mt-2 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">{terminal}</p>
              ) : null}
              <code className="overflow-x-auto whitespace-nowrap border border-foreground bg-background px-3 py-2 text-xs">
                {command}
              </code>
            </div>
          ))}
        </div>
      </footer>
    </main>
  );
}
