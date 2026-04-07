"use client";

import { EntityResponse } from "../lib/api";
import InfoboxDisplay from "./InfoboxDisplay";
import RelationsList from "./RelationsList";
import SectionTabs from "./SectionTabs";

interface EntityCardProps {
  entity: EntityResponse | null;
  loading?: boolean;
  error?: string | null;
}

export default function EntityCard({ entity, loading = false, error = null }: EntityCardProps) {
  const fallbackName = entity?.name ?? "Aucune entite selectionnee";
  const fallbackType = entity?.type ?? "unknown";

  return (
    <aside className="card fade-in rounded-2xl p-5 md:p-6">
      <h3 className="text-2xl tracking-wide [font-family:var(--font-display)]">{fallbackName}</h3>
      <p className="mb-4 text-xs uppercase tracking-[0.2em] text-gold">{fallbackType}</p>

      {loading ? <p className="text-sm text-[#bba884]">Chargement de la fiche...</p> : null}
      {error ? <p className="text-sm text-ember">{error}</p> : null}
      {!entity && !loading && !error ? (
        <p className="text-sm text-[#bba884]">Pose une question puis clique sur les sources pour charger une fiche.</p>
      ) : null}

      {entity ? (
        <SectionTabs
          tabs={[
            { id: "infobox", label: "Infobox" },
            { id: "relations", label: "Relations" },
          ]}
          render={(tabId) => {
            if (tabId === "relations") {
              return <RelationsList relations={entity.relations} />;
            }
            return <InfoboxDisplay infobox={entity.infobox} />;
          }}
        />
      ) : null}
    </aside>
  );
}
