"use client";

import { useEffect, useState } from "react";

import ChatInterface from "../components/ChatInterface";
import EntityCard from "../components/EntityCard";
import GraphViewer from "../components/GraphViewer";
import SpoilerFilter from "../components/SpoilerFilter";
import { EntityResponse, fetchEntity, fetchGraph, GraphResponse } from "../lib/api";

export default function HomePage() {
  const [spoilerLimit, setSpoilerLimit] = useState("Aucun");
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [entity, setEntity] = useState<EntityResponse | null>(null);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [entityLoading, setEntityLoading] = useState(false);
  const [graphLoading, setGraphLoading] = useState(false);
  const [entityError, setEntityError] = useState<string | null>(null);
  const [graphError, setGraphError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedEntity) {
      setEntity(null);
      setGraph(null);
      setEntityError(null);
      setGraphError(null);
      return;
    }

    let cancelled = false;
    setEntityLoading(true);
    setGraphLoading(true);
    setEntityError(null);
    setGraphError(null);

    fetchEntity(selectedEntity)
      .then((payload) => {
        if (!cancelled) {
          setEntity(payload);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setEntity(null);
          setEntityError("Impossible de charger la fiche entite.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setEntityLoading(false);
        }
      });

    fetchGraph(selectedEntity, 2)
      .then((payload) => {
        if (!cancelled) {
          setGraph(payload);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setGraph(null);
          setGraphError("Impossible de charger le sous-graphe.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setGraphLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedEntity]);

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 py-6 md:gap-6 md:px-8 md:py-10">
      <header className="fade-in rounded-2xl border border-gold/25 bg-[#0f1d34]/70 p-5 md:p-7">
        <p className="text-xs uppercase tracking-[0.22em] text-gold">Grand Line Intelligence</p>
        <h1 className="text-5xl leading-none tracking-wide [font-family:var(--font-display)] md:text-7xl">One Piece RAG</h1>
        <p className="mt-3 max-w-3xl text-sm text-[#d2c5a8] md:text-base">
          Pose n&apos;importe quelle question sur le canon One Piece. Les reponses sont justifiees par des sources wiki/arcs et
          enrichies par un knowledge graph.
        </p>
      </header>

      <div className="grid gap-5 lg:grid-cols-[1.7fr_1fr]">
        <ChatInterface spoilerLimitArc={spoilerLimit} onPrimaryEntityChange={setSelectedEntity} />
        <div className="space-y-5">
          <SpoilerFilter value={spoilerLimit} onChange={setSpoilerLimit} />
          <EntityCard entity={entity} loading={entityLoading} error={entityError} />
        </div>
      </div>

      <GraphViewer graph={graph} loading={graphLoading} error={graphError} />
    </main>
  );
}
