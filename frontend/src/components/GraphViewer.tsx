import { GraphResponse } from "../lib/api";
import D3ForceGraph from "./D3ForceGraph";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

interface GraphViewerProps {
  graph: GraphResponse | null;
  loading?: boolean;
  error?: string | null;
}

export default function GraphViewer({ graph, loading = false, error = null }: GraphViewerProps) {
  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];

  return (
    <Card className="fade-in">
      <CardHeader>
        <CardTitle>Knowledge Graph</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? <p className="mb-3 text-sm text-muted-foreground">Chargement du graphe...</p> : null}
        {error ? <p className="mb-3 text-sm text-destructive">{error}</p> : null}
        {!nodes.length ? (
          <p className="text-sm text-muted-foreground">Aucun sous-graphe charge.</p>
        ) : (
          <D3ForceGraph nodes={nodes} edges={edges} />
        )}
      </CardContent>
    </Card>
  );
}
