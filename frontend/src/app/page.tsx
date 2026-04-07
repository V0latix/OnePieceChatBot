"use client";

import { useMemo, useState } from "react";

import ChatInterface from "../components/ChatInterface";
import EntityCard from "../components/EntityCard";
import GraphViewer from "../components/GraphViewer";
import SpoilerFilter from "../components/SpoilerFilter";

export default function HomePage() {
  const [spoilerLimit, setSpoilerLimit] = useState("Aucun");

  const demoFacts = useMemo(
    () => [
      "Prime: 3,000,000,000 Berries",
      "Fruit: Hito Hito no Mi, Model: Nika",
      "Affiliation: Straw Hat Pirates",
    ],
    [],
  );

  const demoNodes = useMemo(
    () => [
      { id: "luffy", label: "Monkey D. Luffy" },
      { id: "crew", label: "Straw Hat Pirates" },
      { id: "fruit", label: "Hito Hito no Mi, Model: Nika" },
    ],
    [],
  );

  const demoEdges = useMemo(
    () => [
      { source: "Monkey D. Luffy", target: "Straw Hat Pirates", type: "MEMBER_OF" },
      { source: "Monkey D. Luffy", target: "Hito Hito no Mi, Model: Nika", type: "ATE" },
    ],
    [],
  );

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 py-6 md:gap-6 md:px-8 md:py-10">
      <header className="fade-in rounded-2xl border border-gold/25 bg-[#0f1d34]/70 p-5 md:p-7">
        <p className="text-xs uppercase tracking-[0.22em] text-gold">Grand Line Intelligence</p>
        <h1 className="text-5xl leading-none tracking-wide [font-family:var(--font-display)] md:text-7xl">One Piece RAG</h1>
        <p className="mt-3 max-w-3xl text-sm text-[#d2c5a8] md:text-base">
          Pose n'importe quelle question sur le canon One Piece. Les reponses sont justifiees par des sources wiki/arcs et
          enrichies par un knowledge graph.
        </p>
      </header>

      <div className="grid gap-5 lg:grid-cols-[1.7fr_1fr]">
        <ChatInterface />
        <div className="space-y-5">
          <SpoilerFilter value={spoilerLimit} onChange={setSpoilerLimit} />
          <EntityCard name="Monkey D. Luffy" type="character" facts={demoFacts} />
        </div>
      </div>

      <GraphViewer nodes={demoNodes} edges={demoEdges} />
    </main>
  );
}
