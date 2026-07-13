"use client";

import { EntityResponse } from "../lib/api";
import InfoboxDisplay from "./InfoboxDisplay";
import RelationsList from "./RelationsList";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";

interface EntityCardProps {
  entity: EntityResponse | null;
  loading?: boolean;
  error?: string | null;
}

export default function EntityCard({ entity, loading = false, error = null }: EntityCardProps) {
  const fallbackName = entity?.name ?? "Aucune entite selectionnee";
  const fallbackType = entity?.type ?? "unknown";

  return (
    <Card className="fade-in">
      <CardHeader>
        <CardTitle>{fallbackName}</CardTitle>
        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{fallbackType}</p>
      </CardHeader>
      <CardContent>
        {loading ? <p className="text-sm text-muted-foreground">Chargement de la fiche...</p> : null}
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        {!entity && !loading && !error ? (
          <p className="text-sm text-muted-foreground">
            Pose une question puis clique sur les sources pour charger une fiche.
          </p>
        ) : null}

        {entity ? (
          <Tabs defaultValue="infobox">
            <TabsList>
              <TabsTrigger value="infobox">Infobox</TabsTrigger>
              <TabsTrigger value="relations">Relations</TabsTrigger>
            </TabsList>
            <TabsContent value="infobox">
              <InfoboxDisplay infobox={entity.infobox} />
            </TabsContent>
            <TabsContent value="relations">
              <RelationsList relations={entity.relations} />
            </TabsContent>
          </Tabs>
        ) : null}
      </CardContent>
    </Card>
  );
}
