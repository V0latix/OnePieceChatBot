"use client";

import { useEffect, useReducer, useState } from "react";

import ChatInterface from "../components/ChatInterface";
import EntityCard from "../components/EntityCard";
import GraphViewer from "../components/GraphViewer";
import SearchBar from "../components/SearchBar";
import { EntityResponse, fetchEntity, fetchGraph, GraphResponse } from "../lib/api";

interface PanelState {
  entity: EntityResponse | null;
  graph: GraphResponse | null;
  entityLoading: boolean;
  graphLoading: boolean;
  entityError: string | null;
  graphError: string | null;
}

type PanelAction =
  | { type: "reset" }
  | { type: "loading" }
  | { type: "entity_ok"; payload: EntityResponse }
  | { type: "entity_err" }
  | { type: "entity_done" }
  | { type: "graph_ok"; payload: GraphResponse }
  | { type: "graph_err" }
  | { type: "graph_done" };

const INITIAL: PanelState = {
  entity: null,
  graph: null,
  entityLoading: false,
  graphLoading: false,
  entityError: null,
  graphError: null,
};

function panelReducer(state: PanelState, action: PanelAction): PanelState {
  switch (action.type) {
    case "reset":
      return INITIAL;
    case "loading":
      return { ...INITIAL, entityLoading: true, graphLoading: true };
    case "entity_ok":
      return { ...state, entity: action.payload, entityError: null };
    case "entity_err":
      return { ...state, entity: null, entityError: "Impossible de charger la fiche entite." };
    case "entity_done":
      return { ...state, entityLoading: false };
    case "graph_ok":
      return { ...state, graph: action.payload, graphError: null };
    case "graph_err":
      return { ...state, graph: null, graphError: "Impossible de charger le sous-graphe." };
    case "graph_done":
      return { ...state, graphLoading: false };
  }
}

export default function HomePage() {
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [panel, dispatch] = useReducer(panelReducer, INITIAL);

  useEffect(() => {
    if (!selectedEntity) {
      dispatch({ type: "reset" });
      return;
    }

    let cancelled = false;
    dispatch({ type: "loading" });

    fetchEntity(selectedEntity)
      .then((payload) => {
        if (!cancelled) dispatch({ type: "entity_ok", payload });
      })
      .catch(() => {
        if (!cancelled) dispatch({ type: "entity_err" });
      })
      .finally(() => {
        if (!cancelled) dispatch({ type: "entity_done" });
      });

    fetchGraph(selectedEntity, 2)
      .then((payload) => {
        if (!cancelled) dispatch({ type: "graph_ok", payload });
      })
      .catch(() => {
        if (!cancelled) dispatch({ type: "graph_err" });
      })
      .finally(() => {
        if (!cancelled) dispatch({ type: "graph_done" });
      });

    return () => {
      cancelled = true;
    };
  }, [selectedEntity]);

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 md:px-8 md:py-10">
      <header className="fade-in border border-foreground bg-card p-6 md:p-8">
        <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">Grand Line Intelligence</p>
        <h1 className="mt-2 font-display text-5xl font-extrabold uppercase leading-none tracking-tighter md:text-7xl">
          One Piece RAG
        </h1>
        <p className="mt-4 max-w-3xl text-sm text-muted-foreground md:text-base">
          Pose n&apos;importe quelle question sur le canon One Piece. Les reponses sont justifiees par des sources wiki/arcs et
          enrichies par un knowledge graph.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.7fr_1fr]">
        <ChatInterface onPrimaryEntityChange={setSelectedEntity} />
        <div className="flex flex-col gap-6">
          <SearchBar />
          <EntityCard entity={panel.entity} loading={panel.entityLoading} error={panel.entityError} />
        </div>
      </div>

      <GraphViewer graph={panel.graph} loading={panel.graphLoading} error={panel.graphError} />
    </main>
  );
}
